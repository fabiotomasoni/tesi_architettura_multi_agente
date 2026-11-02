"""Esportazione esplicita di soli metadati, usata dai piloti; nessun report."""
from time import sleep
from uuid import UUID
import httpx

if __package__:
    from .check_trace import validate
else:
    from check_trace import validate


def record_trace(client, row, identifier, *, organization='off', minimization='active'):
    row['trace_verified'] = False
    if not identifier:
        row['trace_error'] = 'not_available'
        return
    try:
        identifier = str(UUID(identifier))
        for _ in range(30):
            response = client.get('/traces/'+identifier)
            response.raise_for_status()
            trace = response.json()
            if trace['summary']['all_spans_finished']:
                validate(trace, organization=organization, minimization=minimization)
                row['trace'] = trace
                row['trace_verified'] = trace['summary']['trace_complete']
                return
            sleep(.1)
        row['trace_error'] = 'unfinished'
    except (ValueError,KeyError,TypeError,httpx.HTTPError):
        row['trace_error'] = 'not_available_or_invalid'
