"""Catalogo MCP e proxy delle fonti: tutto negato salvo template configurati."""
from dataclasses import dataclass
from copy import deepcopy
import json
import os
from secrets import token_hex
from time import perf_counter
from types import MappingProxyType
from typing import Literal
from uuid import UUID

import asyncio
from datetime import datetime, timezone
import httpx
from .models import Contract
from . import runtime
from .ecb_source import DESTINATION as ECB_DESTINATION, BRIDGE_JOB, WIRE_REQUEST, verify_ecb
from .privacy import SensitiveContext, check, view_paths
from .a2a_egress import EgressDenied, authorized_task
from .market_evidence import expected_evidence as market
from .tax_evidence import expected_evidence as tax
from .tracing import callback_trace
from .budgets import BUDGETS

from .ade_source import DESTINATION as ADE_DESTINATION, source_job, publication, AdeEvidence, verify_ade, selected_quotes
TAX_SOURCE=os.environ.get('TESI_TAX_SOURCE','simulated')
if TAX_SOURCE not in {'simulated','ade'} or TAX_SOURCE=='ade' and not runtime.ISOLATED:
    raise RuntimeError('Fonte fiscale non autorizzata per questa modalità')
TOOL_CATALOG_VERSION = '0.4.0'
MARKET_SOURCE = os.environ.get('TESI_MARKET_SOURCE','simulated')
if runtime.EXPERIMENT!='off' and (MARKET_SOURCE!='simulated' or TAX_SOURCE!='simulated' or os.environ.get('TESI_MCP_PROFILE','nominal')!='nominal'):
    raise RuntimeError('Il profilo comparativo ammette soltanto fixture nominali fissate')
if MARKET_SOURCE not in {'simulated','ecb'}:
    raise RuntimeError('Fonte mercati non riconosciuta')
if MARKET_SOURCE=='ecb' and not runtime.ISOLATED:
    raise RuntimeError('La fonte reale richiede la modalità isolata')

# Due implementazioni fissate, non un nome modulo scelto dal chiamante.
MARKET_TOOL_IMPLEMENTATION = os.environ.get('TESI_MARKET_TOOL_IMPLEMENTATION','standard')
if MARKET_TOOL_IMPLEMENTATION not in {'standard','equivalent'}:
    raise RuntimeError('Implementazione MCP mercati non autorizzata')
if MARKET_TOOL_IMPLEMENTATION=='equivalent' and (runtime.EXPERIMENT!='off' or MARKET_SOURCE!='simulated' or TAX_SOURCE!='simulated' or os.environ.get('TESI_MCP_PROFILE','nominal')!='nominal'):
    raise RuntimeError('La sostituzione V-06 richiede la demo nominale con fonti simulate, fuori dal confronto 2x2')


@dataclass(frozen=True)
class ToolRoute:
    module: str
    tool: str
    destination: str
    test_modules: tuple[str, ...] = ()


TOOL_ROUTES = MappingProxyType({
    'S-01': ToolRoute('services.rates_mcp_equivalent' if MARKET_TOOL_IMPLEMENTATION=='equivalent' else 'services.rates_mcp', 'lookup_rates', ECB_DESTINATION if MARKET_SOURCE=='ecb' else 'fixture://simulated-rates-v1'),
    'S-02': ToolRoute('services.tax_mcp', 'lookup_tax', ADE_DESTINATION if TAX_SOURCE=='ade' else 'fixture://simulated-tax-v1'),
})


# Selezione esplicita all'avvio del gateway delle fixture negative già presenti.
# Non proviene da Card, richieste HTTP o output del modello.
_profile = os.environ.get('TESI_MCP_PROFILE', 'nominal')
if (MARKET_SOURCE=='ecb' or TAX_SOURCE=='ade') and _profile!='nominal':
    raise RuntimeError('Fixture negative non ammesse insieme alla fonte reale')
if _profile != 'nominal':
    _profiles = {
        'market_timeout': {'S-01':'services.slow_rates_mcp'},
        'missing_source': {'S-01':'services.missing_source_mcp','S-02':'services.missing_source_mcp'},
    }
    if _profile not in _profiles:
        raise RuntimeError('Profilo MCP di laboratorio non riconosciuto')
    TOOL_ROUTES = MappingProxyType({key: (
        ToolRoute(route.module, route.tool, route.destination, (_profiles[_profile][key],))
        if _profile == 'market_timeout' and key in _profiles[_profile]
        else ToolRoute(_profiles[_profile].get(key, route.module), route.tool, route.destination))
        for key, route in TOOL_ROUTES.items()})


class ToolRequest(Contract):
    correlation_id: UUID
    scenario: Literal['S-01', 'S-02']
    tool: str
    arguments: dict
    server_module: str | None = None


class ToolPermit(Contract):
    module: str
    tool: str
    destination: str
    source_token: str
    arguments: dict


class SourceRequest(ToolRequest):
    destination: str
    method: Literal['POST'] = 'POST'
    headers: dict[str, str]


@callback_trace('tool_authorization')
def authorize_tool(broker, request, authorization):
    token = authorization[7:] if authorization and authorization.startswith('Bearer ') else None
    with broker._lock:
        grant = broker._grants.get(token)
        if grant is None or grant.tool_used or grant.task.correlation_id != request.correlation_id or grant.task.scenario != request.scenario:
            raise EgressDenied('Strumento non autorizzato')
        _, task = authorized_task(grant.task)
        route = TOOL_ROUTES[task.scenario]
        inspected=request.model_dump(mode='json',exclude={'correlation_id','scenario'})
        if runtime.UNMINIMIZED:
            from .lab_profile import inspectable_view
            if inspectable_view(request.arguments)!=task.view.model_dump(mode='json'):raise EgressDenied('Profilo finanziario MCP difforme')
            inspected.pop('arguments')
        check(broker._privacy.get(grant.session_id,SensitiveContext()),inspected,allowed_paths=view_paths(('arguments',)))
        expected = task.view.model_dump(mode='json')
        # Confronto canonico: niente coercizioni che nascondano testo aggiuntivo.
        if request.tool != route.tool or json.dumps(request.arguments, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise EgressDenied('Argomenti MCP non autorizzati')
        module = request.server_module or route.module
        if module not in (route.module, *route.test_modules):
            raise EgressDenied('Server MCP non autorizzato')
        grant.tool_used = True
        grant.tool_module = module
        grant.source_token = token_hex(32)
        return ToolPermit(module=module, tool=route.tool, destination=route.destination,
                          source_token=grant.source_token, arguments=expected)


@callback_trace('source_proxy', source=True)
async def source_request(broker, request, authorization):
    token = authorization[7:] if authorization and authorization.startswith('Bearer ') else None
    with broker._lock:
        grant_token, grant = next(((k,g) for k,g in broker._grants.items() if g.source_token and g.source_token == token), (None,None))
        if grant is None or grant.source_used or grant.task.correlation_id != request.correlation_id or grant.task.scenario != request.scenario:
            raise EgressDenied('Fonte non autorizzata')
        _, task = authorized_task(grant.task)
        route = TOOL_ROUTES[task.scenario]
        inspected=request.model_dump(mode='json',exclude={'correlation_id','scenario'})
        if runtime.UNMINIMIZED:
            from .lab_profile import inspectable_view
            if inspectable_view(request.arguments)!=task.view.model_dump(mode='json'):raise EgressDenied('Profilo finanziario MCP difforme')
            inspected.pop('arguments')
        check(broker._privacy.get(grant.session_id,SensitiveContext()),inspected,allowed_paths=view_paths(('arguments',)))
        expected = task.view.model_dump(mode='json')
        if (request.server_module is not None or request.tool != route.tool or request.destination != route.destination or request.method != 'POST'
                or request.headers != {} or json.dumps(request.arguments, sort_keys=True) != json.dumps(expected, sort_keys=True)):
            raise EgressDenied('Richiesta fonte fuori catalogo')
        grant.source_used = True
    started = perf_counter()
    if route.destination.startswith('fixture://'):
        expected_destination = 'fixture://simulated-rates-v1' if task.scenario == 'S-01' else 'fixture://simulated-tax-v1'
        if route.destination != expected_destination:
            raise EgressDenied('Fixture non configurata')
        evidence = (market if task.scenario == 'S-01' else tax)(task.view).model_dump(mode='json')
    elif route.destination == ADE_DESTINATION:
        if task.scenario!='S-02' or not runtime.ISOLATED or broker.bridge is None:
            raise EgressDenied('Percorso AdE non autorizzato')
        p=publication(task.view.tax_year)
        wire={'method':'GET','url':p['source_url'],'headers':{'accept':'application/pdf','accept-encoding':'identity'}}
        check(broker._privacy.get(grant.session_id,SensitiveContext()),wire,public_paths=frozenset({('url',),('headers','accept'),('headers','accept-encoding')}))
        seconds=min(BUDGETS.source_seconds,(task.deadline-datetime.now(timezone.utc)).total_seconds())
        reply=await broker.bridge.infer(source_job(task.view.tax_year),seconds,owner=grant_token)
        body=reply['body']
        if set(body)!=set(p)|{'retrieved_at'} or any(body[k]!=v for k,v in p.items()):
            raise EgressDenied('Ricevuta pubblicazione AdE difforme')
        parsed,_=verify_ade({'source_id':'ade-annual-mortgage-v1','simulated':False,**body,'quotes':selected_quotes(task.view.tax_year,task.view.purpose),'purpose':task.view.purpose},task.view)
        evidence=parsed.model_dump(mode='json')
        grant.external_http_ms=reply['source_ms'];grant.external_http_requests=1
    elif route.destination == ECB_DESTINATION:
        if task.scenario!='S-01' or not runtime.ISOLATED or broker.bridge is None:
            raise EgressDenied('Percorso BCE non autorizzato')
        # Template pubblico fisso: nessun valore del fascicolo entra nella richiesta.
        context=broker._privacy.get(grant.session_id,SensitiveContext())
        check(context,WIRE_REQUEST,public_paths=frozenset({('url',),('headers','accept'),('headers','accept-encoding')}))
        seconds=min(BUDGETS.source_seconds,(task.deadline-datetime.now(timezone.utc)).total_seconds())
        reply=await broker.bridge.infer(BRIDGE_JOB,seconds,owner=grant_token)
        parsed,_=verify_ecb(reply['body'])
        evidence=parsed.model_dump(mode='json')
        grant.external_http_ms=reply['source_ms']
        grant.external_http_requests=1
    else:
        # Solo configurazione fidata può scegliere un endpoint HTTP. Nessuno
        # configurato in produzione: nei test il trasporto è simulato.
        url = httpx.URL(route.destination)
        if url.scheme not in {'http', 'https'} or url.userinfo or url.query or url.fragment:
            raise EgressDenied('Endpoint fonte non configurabile')
        seconds = min(BUDGETS.source_seconds, (task.deadline - datetime.now(timezone.utc)).total_seconds())
        async with asyncio.timeout(max(0, seconds)):
            async with httpx.AsyncClient(timeout=seconds, trust_env=False, follow_redirects=False) as client:
                response = await client.post(route.destination, json=expected)
                if 300 <= response.status_code < 400:
                    raise EgressDenied('Redirect fonte non autorizzato')
                response.raise_for_status()
                evidence = response.json()
    with broker._lock:
        if not any(g is grant for g in broker._grants.values()):
            raise EgressDenied('Autorizzazione fonte revocata')
        authorized_task(task)
        grant.source_evidence = deepcopy(evidence)
        grant.source_completed = True
        grant.source_ms = round((perf_counter() - started)*1000, 3)
    return evidence
