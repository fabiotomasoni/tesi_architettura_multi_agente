"""Inferenza locale autorizzata per incarico; nessuna URL o prompt dal chiamante."""
import asyncio
from dataclasses import dataclass
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
from .privacy import SensitiveContext, check, PRIVACY_VERSION, view_paths
from .a2a_egress import authorized_task, EgressDenied
from .market_evidence import verify_evidence as verify_market
from .tax_evidence import verify_evidence as verify_tax

OLLAMA_ENDPOINT = 'http://127.0.0.1:11434/api/chat'
INFERENCE_CATALOG_VERSION = '0.1.0'
MODELS = MappingProxyType({'S-01': 'llama3.2:3b', 'S-02': 'qwen3:1.7b'})
PROMPTS = {
    'S-01': 'Scrivi in italiano due frasi che descrivono la fixture simulata. Non dare consigli, non dichiarare convenienza e non inventare informazioni. Specifica che non sono dati di mercato reali.',
    'S-02': 'Scrivi in italiano due frasi che descrivono la fixture simulata. Non dare consigli, non dichiarare convenienza e non inventare informazioni. Specifica che sono riferimenti fiscali inventati per test, non normativa reale. Non dichiarare diritti a detrazioni. /no_think',
}


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


@dataclass
class Grant:
    session_id: UUID
    task: object
    tool_used: bool = False
    source_token: str | None = None
    source_used: bool = False
    source_completed: bool = False
    source_ms: float = 0.0
    used: bool = False
    completed: bool = False


class InferenceBroker:
    def __init__(self):
        self._grants = {}
        self._privacy = {}
        self._lock = RLock()

    async def delegate(self, session_id, task, remote):
        _, checked = authorized_task(task)
        check(self._privacy.get(session_id,SensitiveContext()),checked.view.model_dump(mode='json'),allowed_paths=view_paths())
        token = token_hex(32)
        checked = checked.model_copy(update={'inference_token': token})
        with self._lock:
            grant = Grant(session_id, checked)
            self._grants[token] = grant
        try:
            result = await remote(checked)
            result.measurements.update({'gateway_inference_authorized': int(grant.used),
                                        'gateway_inference_completed': int(grant.completed),
                                        'gateway_tool_authorized':int(grant.tool_used),
                                        'gateway_source_authorized':int(grant.source_used),
                                        'gateway_source_completed':int(grant.source_completed),
                                        'gateway_source_ms':grant.source_ms,
                                        'privacy_version':PRIVACY_VERSION,
                                        'tool_catalog_version':'0.1.0',
                                        'inference_catalog_version': INFERENCE_CATALOG_VERSION})
            return result
        finally:
            with self._lock:
                self._grants.pop(token, None)

    def revoke(self, session_id=None):
        with self._lock:
            if session_id is None:self._privacy.clear()
            else:self._privacy.pop(session_id,None)
            for key in list(self._grants):
                if session_id is None or self._grants[key].session_id == session_id:
                    del self._grants[key]

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
            inspected=evidence.model_dump(mode='json')
            # Solo dopo verifica esatta del catalogo: origine pubblica simulata,
            # anche se il numero/data coincide con un valore della sessione.
            check(self._privacy.get(grant.session_id,SensitiveContext()),inspected,
                  allowed_paths=view_paths(),
                  public_paths=frozenset({('reference_date',),('annual_rate_percent',)}))
            # Anche un timeout consuma l'autorizzazione: nessun retry implicito.
            grant.used = True
        payload = {'model': MODELS[task.scenario], 'stream': False, 'keep_alive': 0,
                   'options': {'num_ctx': 4096, 'num_predict': 200, 'temperature': 0},
                   'messages': [{'role': 'system', 'content': PROMPTS[task.scenario]},
                                {'role': 'user', 'content': json.dumps(evidence.model_dump(mode='json'))}]}
        if task.scenario == 'S-02':
            payload['think'] = False
        seconds = min(90, (task.deadline - datetime.now(timezone.utc)).total_seconds())
        started = perf_counter()
        async with asyncio.timeout(max(0, seconds)):
            async with httpx.AsyncClient(timeout=seconds, trust_env=False, follow_redirects=False) as client:
                response = await client.post(OLLAMA_ENDPOINT, json=payload)
                if 300 <= response.status_code < 400:
                    raise EgressDenied('Redirect inferenza non autorizzato')
                response.raise_for_status()
                body = response.json()
        ollama_ms = round((perf_counter() - started)*1000, 3)
        # Una revoca mentre il modello risponde impedisce la consegna tardiva.
        with self._lock:
            if self._grants.get(token) is not grant:
                raise EgressDenied('Autorizzazione inferenza revocata')
            authorized_task(task)
        result = InferenceResponse(model=MODELS[task.scenario], summary=body['message']['content'],
                                 ollama_ms=ollama_ms, prompt_tokens=body['prompt_eval_count'], output_tokens=body['eval_count'],
                                 model_load_ms=round(body['load_duration']/1e6, 3))

        with self._lock:
            if self._grants.get(token) is not grant:
                raise EgressDenied('Autorizzazione inferenza revocata')
            grant.completed = True
        return result
