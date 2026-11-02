"""Adattatore MCP: usa esclusivamente il proxy del gateway per la fonte."""
import os
from gateway.budgets import BUDGETS
import httpx
from gateway.identity import callback_headers
from gateway import runtime


def fetch_source(tool, arguments):
    required = ('TESI_SOURCE_TOKEN', 'TESI_CORRELATION_ID', 'TESI_SCENARIO', 'TESI_SOURCE_DESTINATION', 'TESI_SOURCE_GATEWAY')
    if any(not os.environ.get(key) for key in required):
        return {'status':'blocked', 'error_code':'not_authorized'}
    # URL e autorizzazione sono iniettate dal client applicativo fidato,
    # mai ricavate dal testo di una risposta MCP.
    if runtime.ISOLATED and os.environ['TESI_SOURCE_GATEWAY'] != runtime.GATEWAY_ENDPOINTS[os.environ['TESI_SCENARIO']] + '/internal/sources':
        return {'status':'blocked', 'error_code':'not_authorized'}
    with httpx.Client(timeout=BUDGETS.source_seconds+BUDGETS.transport_grace_seconds, trust_env=False, follow_redirects=False) as client:
        response = client.post(os.environ['TESI_SOURCE_GATEWAY'],
            headers={**callback_headers(os.environ['TESI_SCENARIO']), 'Authorization':'Bearer '+os.environ['TESI_SOURCE_TOKEN']}, json={
                'correlation_id':os.environ['TESI_CORRELATION_ID'], 'scenario':os.environ['TESI_SCENARIO'],
                'tool':tool, 'arguments':arguments, 'destination':os.environ['TESI_SOURCE_DESTINATION'],
                'method':'POST', 'headers':{}})
        if response.status_code == 403 or 300 <= response.status_code < 400:
            return {'status':'blocked', 'error_code':'not_authorized'}
        if response.status_code == 504:
            return {'status':'failed', 'error_code':'timeout'}
        response.raise_for_status()
        return response.json()
