"""Contatori host dichiarati, senza URL, payload o dettagli di eccezioni."""
from contextlib import contextmanager
from contextvars import ContextVar

_execution = ContextVar('authorized_host_http_observation', default=None)


@contextmanager
def observe_execution():
    values = {'kind':None, 'dispatch_attempts':0, 'responses_observed':0}
    token = _execution.set(values)
    try:
        yield values
    finally:
        _execution.reset(token)


def select(kind):
    if kind not in {'ollama','ecb','ade'}:
        raise ValueError('Categoria host non ammessa')
    values = _execution.get()
    if values is not None:
        values['kind'] = kind


def dispatch():
    values = _execution.get()
    if values is not None:
        values['dispatch_attempts'] += 1


def response():
    values = _execution.get()
    if values is not None:
        values['responses_observed'] += 1


def validate_execution(value, job_kind):
    if value is None:
        return
    if not isinstance(value,dict) or set(value)!={'kind','dispatch_attempts','responses_observed'}:
        raise ValueError('Osservazione host non valida')
    expected = {'ecb_market_source':'ecb', 'ade_tax_source':'ade','inference':'ollama'}[job_kind]
    if value['kind'] not in {None,expected,'controlled_fixture'}:
        raise ValueError('Categoria host difforme')
    for key in ('dispatch_attempts','responses_observed'):
        if type(value[key]) is not int or not 0<=value[key]<=1:
            raise ValueError('Contatore host non valido')
    if value['responses_observed']>value['dispatch_attempts'] or (value['kind'] in (None,'controlled_fixture') and value['dispatch_attempts']!=0):
        raise ValueError('Contatori host incoerenti')
