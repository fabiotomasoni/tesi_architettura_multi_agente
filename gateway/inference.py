"""Inferenza locale autorizzata per incarico; nessuna URL o prompt dal chiamante."""
import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from secrets import token_hex
from threading import RLock
from time import perf_counter
from types import MappingProxyType
from typing import Literal
from uuid import UUID

import httpx
from pydantic import Field
from .models import Contract
from . import runtime
from .privacy import SensitiveContext, check, PRIVACY_VERSION, view_paths
from .a2a_egress import authorized_task, EgressDenied
from .market_evidence import verify_evidence as verify_market
from .ecb_source import public_prompt_data
from .agent_contracts import is_ecb_evidence
from .tax_evidence import verify_evidence as verify_tax
from .ade_source import is_ade
from .tracing import context, Span, callback_trace, AGENT_METRICS
from .budgets import BUDGETS
from .market_analysis import build_analysis_input, market_payload, review_for_display, MARKET_ANALYSIS_PROMPT
from .tax_analysis import build_analysis_input as tax_input, tax_payload, review_for_display as review_tax, TAX_ANALYSIS_PROMPT

OLLAMA_ENDPOINT = 'http://127.0.0.1:11434/api/chat'
INFERENCE_CATALOG_VERSION = '0.6.0'
MODELS = MappingProxyType({'S-01': 'llama3.2:3b', 'S-02': 'llama3.2:3b' if runtime.EXPERIMENT!='off' else 'qwen3:1.7b'})
PROMPTS = {'S-01': MARKET_ANALYSIS_PROMPT, 'S-02': TAX_ANALYSIS_PROMPT}


class InferenceRequest(Contract):
    correlation_id: UUID
    scenario: Literal['S-01', 'S-02']
    evidence: dict


class InferenceResponse(Contract):
    model: str
    summary: str = Field(max_length=2000)
    ollama_ms: float = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    model_load_ms: float = Field(ge=0)
    market_analysis: dict | None = None
    tax_analysis: dict | None = None


@dataclass
class Grant:
    session_id: UUID
    task: object
    reference_token: str | None = None
    reference_used: bool = False
    reference_evidence: dict | None = None
    tool_used: bool = False
    tool_module: str | None = None
    source_token: str | None = None
    source_used: bool = False
    source_evidence: dict | None = None
    external_http_ms: float | None = None
    external_http_requests: int = 0
    source_completed: bool = False
    source_ms: float | None = None
    used: bool = False
    completed: bool = False
    market_analysis: dict | None = None
    tax_analysis: dict | None = None
    bridge_roundtrip_ms: float | None = None
    trace_context: object = field(default=None, repr=False)


class InferenceBroker:
    def __init__(self):
        self.bridge = None
        self._grants = {}
        self._privacy = {}
        self._lab_profiles = {}
        self._lock = RLock()
        self.require_session = False

    async def delegate(self, session_id, task, remote):
        _, checked = authorized_task(task)
        if runtime.UNMINIMIZED:
            if self._lab_profiles.get(session_id)!=checked.view.model_dump(mode='json'):
                raise EgressDenied('Profilo laboratorio non corrispondente alla sessione autorizzata')
        else:
            check(self._privacy.get(session_id,SensitiveContext()),checked.view.model_dump(mode='json'),allowed_paths=view_paths())
        token = token_hex(32)
        checked = checked.model_copy(update={'inference_token': token})
        with self._lock:
            if self.require_session and session_id not in self._privacy:
                raise EgressDenied('Sessione già chiusa; nessuna nuova delega autorizzata')
            grant = Grant(session_id, checked, trace_context=context())
            self._grants[token] = grant
        agent_metrics = None
        try:
            result = await remote(checked)
            agent_metrics = getattr(result, 'measurements', {})
            with self._lock:
                if self._grants.get(token) is not grant:
                    raise EgressDenied('Delega revocata; risultato tardivo escluso')
            from .tool_egress import MARKET_SOURCE, TAX_SOURCE, TOOL_CATALOG_VERSION
            if getattr(result,'status',None)=='completed' and ((checked.scenario=='S-01' and (MARKET_SOURCE=='ecb' or is_ecb_evidence(getattr(result,'evidence',None)))) or (checked.scenario=='S-02' and (TAX_SOURCE=='ade' or is_ade(getattr(result,'evidence',None))))):
                if (not grant.source_completed or grant.source_evidence is None or result.evidence is None
                        or result.evidence.model_dump(mode='json') != grant.source_evidence):
                    raise EgressDenied('Risultato della fonte difforme dalla ricevuta del gateway')
            from . import verification_config
            reference=getattr(result,'reference',None)
            if reference is not None or verification_config.SHARED and getattr(result,'status',None)=='completed':
                from .shared_reference import verify as verify_reference
                if reference is None or reference!=grant.reference_evidence:
                    raise EgressDenied('Riferimento difforme dalla ricevuta del gateway')
                verify_reference(reference,checked.scenario,verification_config.PROFILE)
                result.measurements['gateway_reference_receipt_verified']=1
            received_evidence=getattr(result,'evidence',None)
            analysis_field = 'market_analysis' if checked.scenario == 'S-01' else 'tax_analysis'
            returned_analysis = getattr(result, analysis_field, None)
            saved_analysis = getattr(grant, analysis_field)
            matched = grant.completed and saved_analysis is not None and returned_analysis == saved_analysis
            if (returned_analysis is not None or (getattr(result, 'status', None) == 'completed' and saved_analysis is not None)) and not matched:
                raise EgressDenied('Analisi specialista difforme dalla risposta del gateway')
            if matched and getattr(result, 'model', None) != MODELS[checked.scenario]:
                raise EgressDenied('Modello specialista difforme')
            result.measurements['gateway_analysis_receipt_verified'] = int(matched)
            if runtime.EXPERIMENT!='off':
                from .disclosure import view_metrics
                result.measurements['view_metric_scope']='canonical_authorized_financial_content_not_wire_delivery_proof'
                result.measurements.update(view_metrics(checked.view,'a2a_view'))
                if grant.tool_used:
                    from .financial_context import source_arguments
                    result.measurements.update(view_metrics(source_arguments(checked.view),'mcp_arguments'))
                if grant.used:result.measurements.update(view_metrics(checked.view,'model_context'))
            result.measurements['gateway_source_receipt_verified']=int(grant.source_completed and received_evidence is not None and received_evidence.model_dump(mode='json')==grant.source_evidence)
            if grant.external_http_ms is not None:
                result.measurements.update(external_http_ms=grant.external_http_ms,external_http_requests=grant.external_http_requests)
            result.measurements.update({'gateway_inference_authorized': int(grant.used),
                                        'gateway_inference_completed': int(grant.completed),
                                        'gateway_tool_authorized':int(grant.tool_used),
                                        'gateway_source_authorized':int(grant.source_used),
                                        'gateway_source_completed':int(grant.source_completed),
                                        'privacy_version':PRIVACY_VERSION,
                                        'runtime_mode':runtime.MODE,
                                        'workload_identity_enforced':int(runtime.ISOLATED),
                                        'tool_catalog_version':TOOL_CATALOG_VERSION,
                                        'inference_catalog_version': INFERENCE_CATALOG_VERSION})
            if grant.tool_module is not None:
                result.measurements['gateway_tool_module'] = grant.tool_module
            if grant.source_ms is not None:
                result.measurements['gateway_source_ms']=grant.source_ms
            if grant.bridge_roundtrip_ms is not None:
                result.measurements['gateway_bridge_roundtrip_ms']=grant.bridge_roundtrip_ms
            return result
        finally:
            # Dichiarazioni dell'agente, non misure indipendenti del gateway.
            # Un guasto prima del risultato lascia le metriche non disponibili.
            with Span('agent_measurements', checked.scenario, checked.correlation_id) as observation:
                for name in AGENT_METRICS:
                    value = (agent_metrics or {}).get(name)
                    import math
                    observation.metric(**{name:value if type(value) in (int,float) and math.isfinite(value) and value >= 0 else None})
            with self._lock:
                self._grants.pop(token, None)
                if self.bridge is not None:
                    self.bridge.revoke(token)

    def revoke(self, session_id=None):
        with self._lock:
            if session_id is None:
                self._lab_profiles.clear()
                self._privacy.clear()
            else:
                self._lab_profiles.pop(session_id,None)
                self._privacy.pop(session_id,None)
            for key in list(self._grants):
                if session_id is None or self._grants[key].session_id == session_id:
                    del self._grants[key]
                    if self.bridge is not None:
                        self.bridge.revoke(key)

    @callback_trace('model_proxy')
    async def infer(self, request, authorization):
        token = authorization.removeprefix('Bearer ') if authorization and authorization.startswith('Bearer ') else None
        with self._lock:
            grant = self._grants.get(token)
            if grant is None or grant.used or grant.task.correlation_id != request.correlation_id or grant.task.scenario != request.scenario:
                raise EgressDenied('Inferenza non autorizzata')
            _, task = authorized_task(grant.task)
            try:
                verify = verify_market if request.scenario == 'S-01' else verify_tax
                evidence, _ = verify(request.evidence, task.view)
            except Exception:
                raise EgressDenied('Evidenza inferenza non autorizzata') from None
            real_tax=request.scenario=='S-02' and is_ade(evidence)
            real = request.scenario=='S-01' and is_ecb_evidence(evidence)
            if (real or real_tax) and (not grant.source_completed or evidence.model_dump(mode='json') != grant.source_evidence):
                raise EgressDenied('Evidenza istituzionale non recuperata dal gateway')
            packet = tax_input(task.view, evidence) if request.scenario == 'S-02' else build_analysis_input(task.view, evidence)
            inspected = packet['evidence']
            # Solo dopo verifica esatta del catalogo: origine pubblica simulata,
            # anche se il numero/data coincide con un valore della sessione.
            # Gli estratti pubblici sono già confrontati esattamente con catalogo e ricevuta.
            # Non sono testo del fascicolo: sottostringhe come Riva/rivalutazione non sono divulgazioni.
            privacy_payload={k:v for k,v in inspected.items() if k!='rule_quotes'} if request.scenario == 'S-02' else inspected
            check(self._privacy.get(grant.session_id,SensitiveContext()),privacy_payload,
                  allowed_paths=view_paths(),
                  public_paths=frozenset({('reference_date',),('annual_rate_percent',),('observation_period',),('series_key',),('tax_year',),('publication_year',),('quotes',0,'text'),('quotes',1,'text'),('quotes',2,'text'),('quotes',0,'page'),('quotes',1,'page'),('quotes',2,'page')}))
            # Anche un timeout consuma l'autorizzazione: nessun retry implicito.
            grant.used = True
        # Ripetere il controllo della vista prima di entrambe le inferenze.
        if runtime.UNMINIMIZED:
            if self._lab_profiles.get(grant.session_id) != task.view.model_dump(mode='json'):
                raise EgressDenied('Contesto laboratorio non autorizzato')
        else:
            check(self._privacy.get(grant.session_id, SensitiveContext()), task.view.model_dump(mode='json'), allowed_paths=view_paths())
        if task.scenario == 'S-01':
            payload = market_payload(MODELS[task.scenario], packet)
        else:
            payload = tax_payload(MODELS[task.scenario], packet)
        seconds = min(BUDGETS.model_seconds, (task.deadline - datetime.now(timezone.utc)).total_seconds())
        started = perf_counter()
        if runtime.ISOLATED:
            if self.bridge is None:
                raise RuntimeError('Ponte inferenza obbligatorio non configurato')
            reply = await self.bridge.infer(payload, seconds, owner=token)
            grant.bridge_roundtrip_ms = round((perf_counter() - started)*1000,3)
            body = reply['body']
        else:
            async with asyncio.timeout(max(0, seconds)):
                async with httpx.AsyncClient(timeout=seconds, trust_env=False, follow_redirects=False) as client:
                    with Span('local_model_http', task.scenario, task.correlation_id) as observed:
                        observed.metric(dispatch_attempts=1, responses_observed=0)
                        response = await client.post(OLLAMA_ENDPOINT, json=payload)
                        observed.metric(responses_observed=1, http_status=response.status_code)
                    if 300 <= response.status_code < 400:
                        raise EgressDenied('Redirect inferenza non autorizzato')
                    response.raise_for_status()
                    body = response.json()
        ollama_ms = reply['ollama_ms'] if runtime.ISOLATED else round((perf_counter() - started)*1000, 3)
        # Una revoca mentre il modello risponde impedisce la consegna tardiva.
        with self._lock:
            if self._grants.get(token) is not grant:
                raise EgressDenied('Autorizzazione inferenza revocata')
            authorized_task(task)
        raw_summary = body['message']['content']
        analysis = (review_for_display if task.scenario == 'S-01' else review_tax)(raw_summary, task.view, evidence)
        summary = ('Selezione e commento generati; leggere le qualifiche nel report.' if analysis['status'] == 'available'
                   else 'Selezione del modello disponibile; commento escluso.' if analysis['status'] == 'selection_only'
                   else 'Selezione del modello non utilizzabile; nessuna interpretazione sostitutiva.')
        result = InferenceResponse(model=MODELS[task.scenario], summary=summary,
                                 market_analysis=analysis if task.scenario == 'S-01' else None,
                                 tax_analysis=analysis if task.scenario == 'S-02' else None,
                                 ollama_ms=ollama_ms, prompt_tokens=body['prompt_eval_count'], output_tokens=body['eval_count'],
                                 model_load_ms=round(body['load_duration']/1e6, 3))

        with self._lock:
            if self._grants.get(token) is not grant:
                raise EgressDenied('Autorizzazione inferenza revocata')
            grant.completed = True
            setattr(grant, 'market_analysis' if task.scenario == 'S-01' else 'tax_analysis', deepcopy(analysis))
        return result
