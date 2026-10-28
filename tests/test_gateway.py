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
