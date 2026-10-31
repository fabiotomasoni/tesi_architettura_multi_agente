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

TOOL_CATALOG_VERSION = '0.2.0'
MARKET_SOURCE = os.environ.get('TESI_MARKET_SOURCE','simulated')
if MARKET_SOURCE not in {'simulated','ecb'}:
    raise RuntimeError('Fonte mercati non riconosciuta')
if MARKET_SOURCE=='ecb' and not runtime.ISOLATED:
    raise RuntimeError('La fonte reale richiede la modalità isolata')


@dataclass(frozen=True)
class ToolRoute:
    module: str
    tool: str
    destination: str
    test_modules: tuple[str, ...] = ()


TOOL_ROUTES = MappingProxyType({
    'S-01': ToolRoute('services.rates_mcp', 'lookup_rates', ECB_DESTINATION if MARKET_SOURCE=='ecb' else 'fixture://simulated-rates-v1'),
    'S-02': ToolRoute('services.tax_mcp', 'lookup_tax', 'fixture://simulated-tax-v1'),
})


# Selezione esplicita all'avvio del gateway delle fixture negative già presenti.
# Non proviene da Card, richieste HTTP o output del modello.
_profile = os.environ.get('TESI_MCP_PROFILE', 'nominal')
if MARKET_SOURCE=='ecb' and _profile!='nominal':
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


def authorize_tool(broker, request, authorization):
    token = authorization[7:] if authorization and authorization.startswith('Bearer ') else None
    with broker._lock:
        grant = broker._grants.get(token)
        if grant is None or grant.tool_used or grant.task.correlation_id != request.correlation_id or grant.task.scenario != request.scenario:
            raise EgressDenied('Strumento non autorizzato')
        _, task = authorized_task(grant.task)
        route = TOOL_ROUTES[task.scenario]
        check(broker._privacy.get(grant.session_id,SensitiveContext()),request.model_dump(mode='json',exclude={'correlation_id','scenario'}),allowed_paths=view_paths(('arguments',)))
        expected = task.view.model_dump(mode='json')
        # Confronto canonico: niente coercizioni che nascondano testo aggiuntivo.
        if request.tool != route.tool or json.dumps(request.arguments, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise EgressDenied('Argomenti MCP non autorizzati')
        module = request.server_module or route.module
        if module not in (route.module, *route.test_modules):
            raise EgressDenied('Server MCP non autorizzato')
        grant.tool_used = True
        grant.source_token = token_hex(32)
        return ToolPermit(module=module, tool=route.tool, destination=route.destination,
                          source_token=grant.source_token, arguments=expected)


async def source_request(broker, request, authorization):
    token = authorization[7:] if authorization and authorization.startswith('Bearer ') else None
    with broker._lock:
        grant = next((g for g in broker._grants.values() if g.source_token and g.source_token == token), None)
        if grant is None or grant.source_used or grant.task.correlation_id != request.correlation_id or grant.task.scenario != request.scenario:
            raise EgressDenied('Fonte non autorizzata')
        _, task = authorized_task(grant.task)
        route = TOOL_ROUTES[task.scenario]
        check(broker._privacy.get(grant.session_id,SensitiveContext()),request.model_dump(mode='json',exclude={'correlation_id','scenario'}),allowed_paths=view_paths(('arguments',)))
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
    elif route.destination == ECB_DESTINATION:
        if task.scenario!='S-01' or not runtime.ISOLATED or broker.bridge is None:
            raise EgressDenied('Percorso BCE non autorizzato')
        # Template pubblico fisso: nessun valore del fascicolo entra nella richiesta.
        context=broker._privacy.get(grant.session_id,SensitiveContext())
        check(context,WIRE_REQUEST,public_paths=frozenset({('url',),('headers','accept'),('headers','accept-encoding')}))
        seconds=min(30,(task.deadline-datetime.now(timezone.utc)).total_seconds())
        reply=await broker.bridge.infer(BRIDGE_JOB,seconds)
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
        seconds = min(30, (task.deadline - datetime.now(timezone.utc)).total_seconds())
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
