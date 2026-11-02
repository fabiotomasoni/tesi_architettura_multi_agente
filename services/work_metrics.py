"""Sole misure numeriche locali, restituite anche negli esiti di errore."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter

_metrics = ContextVar('agent_work_metrics', default=None)


def count(name):
    if name not in {'mcp_sessions_started','mcp_tool_calls','mcp_tool_calls_completed'}:
        raise ValueError('Contatore non ammesso')
    current = _metrics.get()
    if current is not None:
        current[name] += 1


@contextmanager
def duration(name):
    if name not in {'mcp_ms','inference_gateway_roundtrip_ms'}:
        raise ValueError('Durata non ammessa')
    began = perf_counter()
    try:
        yield
    finally:
        current = _metrics.get()
        if current is not None:
            current[name] = round((perf_counter()-began)*1000,3)


def observe_work(function):
    @wraps(function)
    async def wrapped(*args, **kwargs):
        values = {'mcp_sessions_started':0, 'mcp_tool_calls':0, 'mcp_tool_calls_completed':0}
        token = _metrics.set(values)
        try:
            result = await function(*args, **kwargs)
            result.measurements.update(values)
            return result
        except BaseException as error:
            # L'eccezione non viene serializzata né stampata. La pipeline ADK
            # può recuperare soltanto questo dizionario di contatori/durate.
            error.work_metrics = values.copy()
            raise
        finally:
            _metrics.reset(token)
    return wrapped
