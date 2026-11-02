"""Traccia locale limitata a categorie chiuse, durate e conteggi.

Nessun logger, corpo HTTP, messaggio di eccezione, URL, credenziale o valore
documentale. Lo stato è volatile e indipendente dai profili cancellati.
"""
import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
import inspect
import math
import re
from threading import RLock
from time import monotonic, perf_counter
from uuid import UUID, uuid4

TRACE_VERSION = '1.0.0'
PHASES = frozenset({
    'upload', 'input_read', 'pdf_prevalidation', 'extraction', 'profile_validation',
    'privacy_context', 'policy_view', 'analysis', 'legacy_workflow', 'legacy_markets',
    'view_request', 'close_request', 'prepare_task', 'delegate', 'verify_result',
    'report', 'presentation', 'cleanup', 'a2a_card', 'a2a_message',
    'tool_authorization', 'source_proxy', 'model_proxy', 'privacy_scan',
    'asgi_delivery', 'agent_measurements', 'bridge_wait', 'local_model_http', 'source_http',
})
OUTCOMES = frozenset({'completed', 'partial', 'blocked', 'failed', 'cancelled', 'unverified'})
ERROR_CODES = frozenset({'timeout','not_authorized','input_not_ready','delegation_failed',
                        'invalid_result','execution_failed','missing_provenance','workflow_error',
                        'operation_failed','cancelled','request_rejected','http_error'})
METRICS = frozenset({
    'http_status', 'input_bytes', 'documents', 'rejected_documents',
    'dispatch_attempts', 'responses_observed', 'asgi_body_complete',
    'prompt_tokens', 'output_tokens', 'ollama_ms', 'model_load_ms',
    'mcp_ms', 'mcp_tool_calls', 'mcp_sessions_started', 'mcp_tool_calls_completed', 'card_validation_ms', 'a2a_roundtrip_ms',
    'inference_gateway_roundtrip_ms', 'source_http_success_receipts',
    'source_http_ms', 'source_fixture', 'policy_active', 'bridge_claimed', 'sessions_removed',
    'host_http_dispatch_attempts', 'host_http_responses_observed', 'public_source_http_dispatch_attempts',
    'local_model_http_dispatch_attempts', 'execution_controlled_fixture',
})
AGENT_METRICS = frozenset({'mcp_ms', 'mcp_tool_calls', 'mcp_sessions_started', 'mcp_tool_calls_completed', 'card_validation_ms',
                          'a2a_roundtrip_ms', 'inference_gateway_roundtrip_ms'})
_current = ContextVar('local_metadata_trace', default=None)
_parent = ContextVar('local_metadata_parent', default=None)
_request_span = ContextVar('local_metadata_request', default=None)


class TraceStore:
    def __init__(self, boot_id, *, capacity=128, max_spans=1024, ttl=3600):
        if capacity < 1 or max_spans < 1 or ttl <= 0:
            raise ValueError('Limiti della traccia non validi')
        self.boot_id = str(UUID(boot_id))
        self.capacity, self.max_spans, self.ttl = capacity, max_spans, ttl
        self._records, self._sessions = {}, {}
        self._lock = RLock()

    def _prune(self):
        now = monotonic()
        for key in list(self._records):
            if now-self._records[key]['_created'] >= self.ttl:
                del self._records[key]
        while len(self._records) > self.capacity:
            del self._records[next(iter(self._records))]
        self._sessions = {sid:key for sid,key in self._sessions.items() if key in self._records}

    def create(self):
        from .budgets import BUDGETS
        from .policy import POLICY_VERSION
        from .privacy import PRIVACY_VERSION, ENTITY_RECOGNIZER_VERSION
        from .tool_egress import TOOL_CATALOG_VERSION
        from . import runtime
        with self._lock:
            key = str(uuid4())
            self._records[key] = {
                '_created': monotonic(), '_start': perf_counter(),
                'trace_version': TRACE_VERSION, 'trace_id': key,
                'gateway_boot_id': self.boot_id, 'profile_created': False, 'profile_closed': False,
                'truncated': False, 'spans': [],
                'configuration':{'policy_version':POLICY_VERSION, 'privacy_version':PRIVACY_VERSION,
                    'entity_recognizer_version':ENTITY_RECOGNIZER_VERSION, 'tool_catalog_version':TOOL_CATALOG_VERSION,
                    'organization':runtime.EXPERIMENT, 'minimization':runtime.MINIMIZATION, 'budgets':BUDGETS.public()},
            }
            self._prune()
            return (self, key)

    def bind_session(self, session_id):
        current = _current.get()
        if current and current[0] is self:
            with self._lock:
                self._prune()
                if current[1] in self._records:
                    self._sessions[UUID(str(session_id))] = current[1]
                    self._records[current[1]]['profile_created'] = True

    def for_session(self, session_id, *, include_closed=False):
        with self._lock:
            self._prune()
            key = self._sessions.get(UUID(str(session_id)))
            row = self._records.get(key)
            return (self, key) if row and (include_closed or not row['profile_closed']) else None

    def closed(self, session_id):
        context = self.for_session(session_id, include_closed=True)
        if context:
            with self._lock:
                self._records[context[1]]['profile_closed'] = True

    def start(self, key, phase, parent, scenario, correlation_id):
        if phase not in PHASES or scenario not in (None, 'S-01', 'S-02', 'BATCH'):
            raise ValueError('Categoria della traccia non valida')
        with self._lock:
            row = self._records.get(key)
            if row is None:
                return None
            if len(row['spans']) >= self.max_spans:
                row['truncated'] = True
                return None
            span = {'span_id':str(uuid4()), 'parent_id':parent,
                    'phase':phase, 'scenario':scenario, 'correlation_id':correlation_id,
                    'start_ms':round((perf_counter()-row['_start'])*1000, 3),
                    'duration_ms':None, 'outcome':None, 'error_code':None, 'metrics':{}}
            if phase == 'model_proxy':
                span['metrics'].update(prompt_tokens=None, output_tokens=None,
                                       ollama_ms=None, model_load_ms=None)
            row['spans'].append(span)
            return span

    def snapshot(self, key):
        with self._lock:
            self._prune()
            record = self._records.get(str(UUID(str(key))))
            if record is None:
                return None
            result = deepcopy({k:v for k,v in record.items() if not k.startswith('_')})
        # Unione di intervalli HTTP, non somma di fasi annidate/concorrenza.
        roots = [s for s in result['spans'] if s['phase'] in
                 {'upload','analysis','legacy_workflow','legacy_markets','view_request','close_request'}
                 and s['duration_ms'] is not None]
        intervals = sorted((s['start_ms'], s['start_ms']+s['duration_ms']) for s in roots)
        total, end = 0.0, 0.0
        for left, right in intervals:
            total += max(0.0, right-max(left, end))
            end = max(end, right)
        models = [s for s in result['spans'] if s['phase']=='model_proxy']
        agents = [s for s in result['spans'] if s['phase']=='agent_measurements']
        source_http = [s for s in result['spans'] if s['phase']=='source_proxy' and s['metrics'].get('source_fixture')==0]
        bridge = [s for s in result['spans'] if s['phase']=='bridge_wait']
        result['summary'] = {
            'backend_request_union_ms':round(total, 3),
            'elapsed_to_last_event_ms':round(max((s['start_ms']+(s['duration_ms'] or 0) for s in result['spans']), default=0), 3),
            'model_proxy_calls':len(models),
            'model_usage_observed':sum(s['metrics']['prompt_tokens'] is not None and s['metrics']['output_tokens'] is not None for s in models),
            'prompt_tokens':sum(s['metrics']['prompt_tokens'] for s in models) if all(s['metrics']['prompt_tokens'] is not None for s in models) else None,
            'output_tokens':sum(s['metrics']['output_tokens'] for s in models) if all(s['metrics']['output_tokens'] is not None for s in models) else None,
            'all_spans_finished':all(s['duration_ms'] is not None for s in result['spans']),
            'a2a_message_dispatch_attempts':sum(s['metrics'].get('dispatch_attempts',0) for s in result['spans'] if s['phase']=='a2a_message'),
            'a2a_card_dispatch_attempts':sum(s['metrics'].get('dispatch_attempts',0) for s in result['spans'] if s['phase']=='a2a_card'),
            'tool_permits_issued':sum(s['phase']=='tool_authorization' and s['outcome']=='completed' for s in result['spans']),
            'callback_denials':sum(s['phase'] in {'tool_authorization','source_proxy','model_proxy'} and s['outcome']=='blocked' for s in result['spans']),
            'mcp_tool_calls_agent_reported':sum(s['metrics']['mcp_tool_calls'] for s in agents) if all(s['metrics'].get('mcp_tool_calls') is not None for s in agents) else None,
            'source_http_success_receipts':sum(s['metrics']['source_http_success_receipts'] for s in source_http) if all(s['metrics'].get('source_http_success_receipts') is not None for s in source_http) else None,
            'host_http_dispatch_attempts':sum(s['metrics']['host_http_dispatch_attempts'] for s in bridge) if all(s['metrics'].get('host_http_dispatch_attempts') is not None for s in bridge) else None,
            'host_http_responses_observed':sum(s['metrics']['host_http_responses_observed'] for s in bridge) if all(s['metrics'].get('host_http_responses_observed') is not None for s in bridge) else None,
        }
        result['summary']['trace_complete'] = (not result['profile_created'] or result['profile_closed']) and not result['truncated'] and result['summary']['all_spans_finished']
        if result['truncated']:
            # Non trasformare un campione incompleto in un totale osservato.
            for key in result['summary']:
                if key not in {'all_spans_finished','trace_complete'}:
                    result['summary'][key] = None
        result['scope'] = 'volatile_gateway_metadata_not_network_capture_or_client_receipt'
        result['semantics'] = {
            'durations':'inclusive_nested_not_additive; agent_measurements_are_agent_reported',
            'model_usage':'runtime_or_bridge_reported; null_if_unavailable; not_a_billing_receipt',
            'source_http':'successful_proxy_receipts_only; failed_or_cancelled_bridge_requests_may_be_unobservable',
            'host_http':'bridge_reported_dispatch_attempts_and_responses; null_without_receipt; not_packet_capture',
            'asgi_delivery':'application_handoff_only_not_client_receipt',
            'retention':'bounded_RAM; lost_on_restart',
        }
        result['retention_limits'] = {'traces':self.capacity, 'spans_per_trace':self.max_spans, 'seconds':self.ttl}
        return result


def context():
    return _current.get()


def trace_id():
    current = context()
    return current[1] if current else None


def request_outcome(outcome):
    if outcome not in OUTCOMES:
        raise ValueError('Esito della traccia non ammesso')
    current = _request_span.get()
    if current is not None:
        current.outcome = outcome
        if outcome=='cancelled':
            current.error('cancelled')


@contextmanager
def use_trace(value):
    token = _current.set(value)
    parent = _parent.set(None)
    try:
        yield
    finally:
        _parent.reset(parent)
        _current.reset(token)


class Span:
    def __init__(self, phase, scenario=None, correlation_id=None):
        if phase not in PHASES or scenario not in (None, 'S-01', 'S-02', 'BATCH'):
            raise ValueError('Categoria della traccia non valida')
        self.current = context()
        self.phase = phase
        correlation_id = str(UUID(str(correlation_id))) if correlation_id is not None else None
        self.row = self.current[0].start(self.current[1], phase, _parent.get(), scenario, correlation_id) if self.current else None
        self.started = perf_counter()
        self.outcome = 'completed'

    def metric(self, **values):
        if any(k not in METRICS or (v is not None and
               (type(v) not in (int,float) or not math.isfinite(v) or v < 0)) for k,v in values.items()):
            raise ValueError('Metrica della traccia non ammessa')
        if self.row is not None:
            with self.current[0]._lock:
                self.row['metrics'].update(values)

    def identify(self, task):
        if task is None:
            return
        scenario, correlation = task.scenario, str(UUID(str(task.correlation_id)))
        if scenario not in {'S-01','S-02','BATCH'}:
            raise ValueError('Scenario non ammesso')
        if self.row is not None:
            with self.current[0]._lock:
                self.row.update(scenario=scenario, correlation_id=correlation)

    def error(self, code):
        if code is not None and code not in ERROR_CODES:
            raise ValueError('Codice della traccia non ammesso')
        if self.row is not None:
            with self.current[0]._lock:
                self.row['error_code'] = code

    def __enter__(self):
        self.token = _parent.set(self.row['span_id'] if self.row else _parent.get())
        return self

    def __exit__(self, kind, value, tb):
        _parent.reset(self.token)
        if kind is not None:
            import httpx
            status = getattr(value,'status_code',None)
            denied = kind.__name__=='EgressDenied' or status in (403,409)
            self.outcome = 'cancelled' if issubclass(kind, asyncio.CancelledError) else 'blocked' if denied else 'failed'
            code = ('cancelled' if self.outcome=='cancelled' else
                    'input_not_ready' if status==409 and self.phase=='policy_view' else
                    'request_rejected' if status==409 else
                    'not_authorized' if denied else
                    'timeout' if issubclass(kind,(TimeoutError,httpx.TimeoutException)) else 'operation_failed')
            self.error(code)
        if self.outcome not in OUTCOMES:
            raise ValueError('Esito della traccia non ammesso')
        if self.row is not None:
            with self.current[0]._lock:
                self.row.update(duration_ms=round((perf_counter()-self.started)*1000,3), outcome=self.outcome)


def measured(phase, *, scenario=None, scenario_parameter=None):
    """Solo categorie fisse; nessun argomento o risultato serializzato."""
    def decorate(function):
        signature = inspect.signature(function)
        def observation(args, kwargs):
            selected = scenario
            if scenario_parameter is not None:
                # Il parametro è un contratto validato; si legge solo la sua
                # categoria, mai il corpo o gli altri campi dell'argomento.
                request = signature.bind(*args, **kwargs).arguments[scenario_parameter]
                selected = request.scenario
            return Span(phase, selected)
        def finish(span, result):
            status = result.get('status') if isinstance(result, dict) else getattr(result, 'status', None)
            if status in OUTCOMES:
                span.outcome = status
            code = result.get('error_code') if isinstance(result,dict) else getattr(result,'error_code',None)
            if code in ERROR_CODES:
                span.error(code)
            if phase=='prepare_task' and isinstance(result,dict):
                span.identify(result.get('task'))
            return result
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def asynchronous(*args, **kwargs):
                with observation(args, kwargs) as span:
                    if phase in {'delegate','verify_result'} and args and isinstance(args[0],dict):
                        span.identify(args[0].get('task'))
                    return finish(span, await function(*args, **kwargs))
            return asynchronous
        @wraps(function)
        def synchronous(*args, **kwargs):
            with observation(args, kwargs) as span:
                if phase in {'delegate','verify_result'} and args and isinstance(args[0],dict):
                    span.identify(args[0].get('task'))
                return finish(span, function(*args, **kwargs))
        return synchronous
    return decorate


def callback_trace(phase, *, source=False):
    """Associa callback solo tramite capacità del gateway, mai via ID del client."""
    def decorate(function):
        signature = inspect.signature(function)
        def selected(args, kwargs):
            arguments = signature.bind(*args, **kwargs).arguments
            broker = arguments.get('broker', arguments.get('self'))
            auth = arguments['authorization']
            token = auth[7:] if auth and auth.startswith('Bearer ') else None
            with broker._lock:
                grant = next((g for g in broker._grants.values() if g.source_token == token and token), None) if source else broker._grants.get(token)
                return grant
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def asynchronous(*args, **kwargs):
                grant = selected(args, kwargs)
                source_already_used = bool(grant and grant.source_used) if source else False
                with use_trace(getattr(grant, 'trace_context', None)), Span(phase, getattr(getattr(grant,'task',None),'scenario',None), getattr(getattr(grant,'task',None),'correlation_id',None)) as span:
                    try:
                        result = await function(*args, **kwargs)
                        if phase == 'model_proxy':
                            span.metric(prompt_tokens=result.prompt_tokens, output_tokens=result.output_tokens,
                                        ollama_ms=result.ollama_ms, model_load_ms=result.model_load_ms)
                        return result
                    finally:
                        if source and grant is not None and grant.source_used and not source_already_used:
                            from .tool_egress import TOOL_ROUTES
                            fixture = TOOL_ROUTES[grant.task.scenario].destination.startswith('fixture://')
                            span.metric(source_fixture=int(fixture),
                                        source_http_success_receipts=0 if fixture else grant.external_http_requests or None,
                                        source_http_ms=grant.external_http_ms)
            return asynchronous
        @wraps(function)
        def synchronous(*args, **kwargs):
            grant = selected(args, kwargs)
            with use_trace(getattr(grant, 'trace_context', None)), Span(phase, getattr(getattr(grant,'task',None),'scenario',None), getattr(getattr(grant,'task',None),'correlation_id',None)):
                return function(*args, **kwargs)
        return synchronous
    return decorate


class TraceMiddleware:
    """ASGI puro: include il parsing multipart; nessuna lettura/copia dei corpi."""
    def __init__(self, app, store):
        self.app, self.store = app, store

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path, method = scope['path'], scope['method']
        phase, selected = None, None
        if method=='POST' and path in {'/sessions','/sessions/pdf'}:
            phase, selected = 'upload', self.store.create()
        else:
            match = re.fullmatch(r'/sessions/([0-9a-fA-F-]{36})(?:/(views|analysis|workflow|markets))?', path)
            if match:
                try:
                    selected = self.store.for_session(match[1])
                except ValueError:
                    pass
                phase = {'views':'view_request','analysis':'analysis','workflow':'legacy_workflow','markets':'legacy_markets',None:'close_request'}.get(match[2])
        if not selected:
            return await self.app(scope, receive, send)
        with use_trace(selected), Span(phase) as root:
            request_token = _request_span.set(root)
            delivery = None
            received_bytes = 0
            async def receive_metadata():
                nonlocal received_bytes
                message = await receive()
                if message['type']=='http.request':
                    received_bytes += len(message.get('body',b''))
                return message
            async def send_metadata(message):
                nonlocal delivery
                if message['type']=='http.response.start':
                    status = message['status']
                    root.metric(http_status=status)
                    if status>=400 and root.outcome=='completed':
                        root.outcome = 'blocked' if status in (403,409) else 'failed'
                        root.error('request_rejected' if status<500 else 'http_error')
                    message = {**message, 'headers':[*message['headers'], (b'x-trace-id', selected[1].encode())]}
                    delivery = Span('asgi_delivery')
                await send(message)
                if message['type']=='http.response.body' and not message.get('more_body',False) and delivery:
                    delivery.metric(asgi_body_complete=1)
                    delivery.__enter__()
                    delivery.__exit__(None,None,None)
                    delivery = None
            try:
                await self.app(scope, receive_metadata, send_metadata)
            finally:
                _request_span.reset(request_token)
                if phase=='upload':
                    root.metric(input_bytes=received_bytes)
                if delivery is not None:
                    delivery.metric(asgi_body_complete=0)
                    delivery.__enter__()
                    delivery.__exit__(RuntimeError, None, None)
