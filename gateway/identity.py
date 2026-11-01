"""Identità di workload locale, distinta dalla capability monouso dell'incarico.

Segreti separati per direzione/ruolo; HTTP confinato alle reti isolate locali.
Non è mTLS e non abilita agenti remoti o trasporti su reti non fidate.
"""
import json
import os
from pathlib import Path
import re
from secrets import compare_digest
from . import runtime

HEADER = 'x-tesi-service-key'
SCENARIO_ROLES = ({'S-01':'generalist','S-02':'generalist','BATCH':'generalist'} if runtime.SINGLE else {'S-01': 'markets', 'S-02': 'tax'})


def load_identity():
    path = os.environ.get('TESI_IDENTITY_FILE')
    if not path:
        raise RuntimeError('Identità del componente non configurata')
    try:
        data = json.loads(Path(path).read_text())
        if data['role'] not in {'gateway', 'markets', 'tax', 'bridge','generalist'}:
            raise ValueError()
        expected = {'gateway': {'gateway_to_markets','gateway_to_tax','markets_to_gateway','tax_to_gateway','bridge'},
                    'markets': {'gateway_to_markets','markets_to_gateway'},
                    'tax': {'gateway_to_tax','tax_to_gateway'}, 'bridge': {'bridge'}}
        expected['generalist']={'gateway_to_generalist','generalist_to_gateway'}
        if runtime.SINGLE:expected['gateway']={'gateway_to_generalist','generalist_to_gateway','bridge'}
        if set(data['keys']) != expected[data['role']]:
            raise ValueError()
        if not data['keys'] or any(not re.fullmatch(r'[0-9a-f]{64}', key) for key in data['keys'].values()):
            raise ValueError()
        return data
    except Exception:
        raise RuntimeError('Configurazione identità non valida') from None


def key_for(name, *, expected_role=None):
    data = load_identity()
    if expected_role and data['role'] != expected_role:
        raise RuntimeError('Ruolo del componente difforme')
    try:
        return data['keys'][name]
    except KeyError:
        raise RuntimeError('Credenziale del ruolo assente') from None


def callback_headers(scenario):
    if not runtime.ISOLATED:
        return {}
    role = SCENARIO_ROLES[scenario]
    return {HEADER: key_for(role + '_to_gateway', expected_role=role)}


def a2a_headers(scenario):
    if not runtime.ISOLATED:
        return {}
    return {HEADER: key_for('gateway_to_' + SCENARIO_ROLES[scenario], expected_role='gateway')}


def matching_key(received, name, role='gateway'):
    return isinstance(received, str) and compare_digest(received, key_for(name, expected_role=role))


class AgentIdentityApp:
    """Rifiuta anche la Card senza identità, prima di entrare in ADK/A2A."""
    def __init__(self, inner, scenario):
        self.inner, self.scenario = inner, scenario
        if runtime.ISOLATED:
            key_for('gateway_to_' + SCENARIO_ROLES[scenario], expected_role=SCENARIO_ROLES[scenario])

    async def __call__(self, scope, receive, send):
        if runtime.ISOLATED and scope['type'] == 'http':
            headers = [(k.lower(), v) for k, v in scope['headers'] if k.lower() == HEADER.encode()]
            role = SCENARIO_ROLES[self.scenario]
            if len(headers) != 1 or not matching_key(headers[0][1].decode('latin1'), 'gateway_to_' + role, role):
                await send({'type': 'http.response.start', 'status': 403,
                            'headers': [(b'content-type', b'application/json')]})
                await send({'type': 'http.response.body', 'body': b'{"detail":"Chiamante non autorizzato"}'})
                return
        await self.inner(scope, receive, send)
