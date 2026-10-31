import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway.app import create_app


@pytest.fixture
def payload():
    return json.loads(Path('examples/session_complete.json').read_text())


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


def create(client, payload):
    response = client.post('/sessions', json=payload)
    assert response.status_code == 201
    return response.json()['session_id']


def test_views_minimize_and_delete(client, payload):
    sid = create(client, payload)
    market = client.post(f'/sessions/{sid}/views', json={'scenario':'S-01','recipient':'markets'})
    assert market.status_code == 200
    assert market.json()['data'] == {'mortgage_type':'residential','rate_type':'fixed','remaining_years_band':{'lower_exclusive':10,'upper_inclusive':15}}
    tax = client.post(f'/sessions/{sid}/views', json={'scenario':'S-02','recipient':'tax'})
    assert tax.json()['data'] == {'tax_year':2025,'expense_category':'mortgage_interest','purpose':'primary_home_purchase'}
    assert client.delete(f'/sessions/{sid}').status_code == 204
    assert client.post(f'/sessions/{sid}/views', json={'scenario':'S-01','recipient':'markets'}).status_code == 404


@pytest.mark.parametrize('change', ['missing','ambiguous','unit','period','negative','fractional'])
def test_invalid_financial_data_blocks_view(client, payload, change):
    fact = payload['profile']['remaining_months']
    if change == 'missing': del payload['profile']['remaining_months']
    elif change == 'ambiguous': fact['status'] = 'ambiguous'
    elif change == 'unit': fact['unit'] = 'year'
    elif change == 'period': fact['period'] = '2024-01-01'
    elif change == 'negative': fact['value'] = -1
    else: fact['value'] = '12.5'
    sid = create(client, payload)
    assert client.post(f'/sessions/{sid}/views', json={'scenario':'S-01','recipient':'markets'}).status_code == 409
    assert client.post(f'/sessions/{sid}/views', json={'scenario':'S-02','recipient':'tax'}).status_code == 200


def test_denied_recipient_and_unrequested_scenario(client, payload):
    payload['scenarios'] = ['S-01']
    sid = create(client, payload)
    for scenario,recipient in [('S-01','tax'),('S-02','tax')]:
        assert client.post(f'/sessions/{sid}/views', json={'scenario':scenario,'recipient':recipient}).status_code == 403


def test_unknown_sensitive_fields_not_echoed(client, payload):
    payload['profile']['iban'] = 'SECRET-TEST'
    response = client.post('/sessions', json=payload)
    assert response.status_code == 422
    assert 'SECRET-TEST' not in response.text


def test_expiry(client, payload, monkeypatch):
    monkeypatch.setattr('gateway.app.SESSION_TTL_SECONDS', -1)
    sid = create(client, payload)
    assert client.delete(f'/sessions/{sid}').status_code == 404


def test_tax_period_mismatch(client, payload):
    payload['profile']['annual_interest']['period'] = '2024-12-31'
    sid = create(client, payload)
    assert client.post(f'/sessions/{sid}/views', json={'scenario':'S-02','recipient':'tax'}).status_code == 409


def test_nonfinite_tax_year_does_not_crash(client, payload):
    payload['profile']['tax_year']['value']='NaN'
    sid=create(client,payload)
    response=client.post(f'/sessions/{sid}/views',json={'scenario':'S-02','recipient':'tax'})
    assert response.status_code==409


def test_abandoned_session_expires_without_new_requests(monkeypatch, payload):
    import importlib
    import threading
    from gateway.inference import InferenceBroker
    module=importlib.import_module('gateway.app')
    broker=InferenceBroker();revoked=threading.Event();clock=[0.0]
    original=broker.revoke
    def revoke(sid=None):
        original(sid)
        if sid is not None:revoked.set()
    broker.revoke=revoke
    monkeypatch.setattr(module,'InferenceBroker',lambda:broker)
    monkeypatch.setattr(module,'monotonic',lambda:clock[0])
    monkeypatch.setattr(module,'SESSION_TTL_SECONDS',1)
    monkeypatch.setattr(module,'SESSION_SWEEP_SECONDS',0.01)
    with TestClient(create_app()) as client:
        sid=create(client,payload)
        assert broker._privacy
        clock[0]=2.0
        # Nessun'altra richiesta HTTP: deve agire il supervisore periodico.
        assert revoked.wait(timeout=1)
        assert not broker._privacy and not broker._grants
        assert client.delete('/sessions/'+sid).status_code==404
