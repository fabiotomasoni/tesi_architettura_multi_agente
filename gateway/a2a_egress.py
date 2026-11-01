"""Confine applicativo A2A locale. Non costituisce isolamento di rete.

Il catalogo è configurazione fidata; Card e risultati non lo estendono.
Inferenza e fonti MCP usano i rispettivi controlli nello stesso gateway.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from types import MappingProxyType
from uuid import UUID

import httpx
from .agent_contracts import MarketTask, TaxTask, BatchTask
from .runtime import AGENT_ENDPOINTS, SINGLE
from . import runtime
from .lab_profile import FullFinancialView
from .identity import a2a_headers


class EgressDenied(ValueError):
    """Diniego senza includere il contenuto della richiesta."""


@dataclass(frozen=True)
class Route:
    endpoint: str
    task_type: type
    agent_name: str
    skill: str


CATALOG_VERSION = '0.1.0'
ROUTES = MappingProxyType({
    'S-01': Route(AGENT_ENDPOINTS['S-01'], MarketTask, 'markets_agent', 'market_rate_context'),
    'S-02': Route(AGENT_ENDPOINTS['S-02'], TaxTask, 'tax_agent', 'tax_context'),
})

if SINGLE:
    ROUTES=MappingProxyType({**ROUTES,'BATCH':Route(AGENT_ENDPOINTS['BATCH'],BatchTask,'generalist_agent','financial_analysis')})


def authorized_task(task):
    try:
        route = ROUTES[task.scenario]
        # Rivalidare anche oggetti costruiti senza validazione o modificati.
        checked = route.task_type.model_validate(task.model_dump(mode='json'))
        if not isinstance(checked,BatchTask) and isinstance(checked.view,FullFinancialView)!=runtime.UNMINIMIZED:
            raise ValueError('Forma della vista incoerente con il profilo di minimizzazione')
        if isinstance(checked,BatchTask):
            if not SINGLE:raise ValueError()
            for item in checked.tasks:authorized_task(item)
        if checked.policy_version != '0.3.0' or checked.deadline <= datetime.now(timezone.utc):
            raise ValueError()
    except Exception:
        raise EgressDenied('Incarico A2A non autorizzato') from None
    return route, checked


class A2AEgressTransport(httpx.AsyncBaseTransport):
    """Controlla la richiesta effettiva generata dall'SDK prima del trasporto.

    L'istanza è vincolata a un solo incarico. Nessuna URL, intestazione o
    estensione fornita dalla Card è inoltrata liberamente.
    """
    def __init__(self, task, *, inner=None):
        self.route, self.task = authorized_task(task)
        self.message_sends=0
        self.inner = inner if inner is not None else httpx.AsyncHTTPTransport(retries=0)

    async def handle_async_request(self, request):
        route, task = authorized_task(self.task)
        url = str(request.url)
        payload = None
        try:
            if request.method == 'GET' and url == route.endpoint + '.well-known/agent-card.json':
                if request.content:
                    raise ValueError()
            elif request.method == 'POST' and url == route.endpoint:
                raw = json.loads(request.content)
                # Ricostruzione da template, inclusi gli unici metadati ammessi.
                rid = raw['id']
                mid = raw['params']['message']['messageId']
                if rid not in {str(UUID(rid)), UUID(rid).hex} or mid not in {str(UUID(mid)), UUID(mid).hex}:
                    raise ValueError()
                text = raw['params']['message']['parts'][0]['text']
                if json.loads(text) != task.model_dump(mode='json'):
                    raise ValueError()
                payload = {'id': rid, 'jsonrpc': '2.0', 'method': 'message/send',
                           'params': {'message': {'kind': 'message', 'messageId': mid,
                           'parts': [{'kind': 'text', 'text': text}], 'role': 'user'}}}
                if raw != payload:
                    raise ValueError()
                # Il testo viene serializzato dal contratto fidato.
                payload['params']['message']['parts'][0]['text'] = task.model_dump_json()
            else:
                raise ValueError()
            allowed = {'host': request.url.netloc.decode(), 'accept': '*/*',
                       'accept-encoding': request.headers.get('accept-encoding'),
                       'connection': 'keep-alive', 'user-agent': f'python-httpx/{httpx.__version__}',
                       'content-type': 'application/json', 'content-length': str(len(request.content))}
            if request.headers.get('accept-encoding') not in {'identity', 'gzip, deflate', 'gzip, deflate, br', 'gzip, deflate, zstd', 'gzip, deflate, br, zstd'}:
                raise ValueError()
            if len(request.headers.multi_items()) != len({k for k, _ in request.headers.multi_items()}):
                raise ValueError()
            if any(allowed.get(k) != v for k, v in request.headers.multi_items()):
                raise ValueError()
            if set(request.extensions) - {'timeout'}:
                raise ValueError()
        except Exception:
            raise EgressDenied('Richiesta A2A fuori catalogo') from None
        outbound = httpx.Request(request.method, url, json=payload) if payload is not None else httpx.Request('GET', url)
        outbound.headers.update(a2a_headers(task.scenario))
        # Timeout locali fissati dal gateway; nessuna estensione arbitraria inoltrata.
        outbound.extensions = {'timeout': {'connect': 5.0, 'read': 125.0, 'write': 5.0, 'pool': 5.0}}
        if request.method=='POST':self.message_sends+=1
        response = await self.inner.handle_async_request(outbound)
        if 300 <= response.status_code < 400:
            await response.aclose()
            raise EgressDenied('Redirect A2A non autorizzato')
        return response

    async def aclose(self):
        await self.inner.aclose()
