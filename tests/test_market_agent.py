import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from pydantic import ValidationError
from gateway.agent_contracts import MarketTask, MarketResult
from services.market_work import perform
from gateway.market_evidence import expected_evidence as fixture_evidence
from gateway.agent_contracts import MarketView

def lookup_rates(**arguments):
    return fixture_evidence(MarketView(**arguments)).model_dump(mode="json")



def task():
    return MarketTask(correlation_id=uuid4(), deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})


def test_contract_rejects_extra_financial_data():
    data = task().model_dump(mode='json')
    data['view']['remaining_principal'] = '100000'
    with pytest.raises(ValidationError): MarketTask.model_validate(data)


def test_provenance_required():
    with pytest.raises(ValidationError):
        MarketResult(correlation_id=uuid4(),status='completed',summary='test',limits=[],model='test')


def test_simulated_source():
    evidence = lookup_rates(**task().view.model_dump())
    assert evidence['simulated'] and evidence['source_id'] == 'simulated-rates-v1'


def test_expired_task_no_execution():
    expired = task().model_copy(update={'deadline':datetime.now(timezone.utc)-timedelta(seconds=1)})
    with pytest.raises(ValueError): asyncio.run(perform(expired))


def test_a2a_response_and_state_cleanup(monkeypatch):
    from fastapi.testclient import TestClient
    import services.market_agent as module
    async def fake_perform(request):
        return MarketResult(correlation_id=request.correlation_id,status='completed',
            evidence=lookup_rates(**request.view.model_dump()),summary='Fixture simulata',limits=['Test senza Ollama'],model='test')
    monkeypatch.setattr(module, 'perform', fake_perform)
    request = task()
    with TestClient(module.app) as client:
        response = client.post('/',json={'jsonrpc':'2.0','id':'test','method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':request.model_dump_json()}]}}})
        assert response.status_code == 200
        assert 'error' not in response.json(), response.text
    assert not module.task_store.tasks
    sessions = asyncio.run(module.session_service.list_sessions(app_name='markets_demo'))
    assert not sessions.sessions


def test_timeout_during_real_mcp_and_cleanup(monkeypatch):
    from time import perf_counter
    from fastapi.testclient import TestClient
    import services.market_agent as module
    from services.market_work import perform
    import services.market_work as work
    from gateway.tool_egress import ToolPermit
    async def permit(t, **kwargs):
        return ToolPermit(module='services.slow_rates_mcp',tool='lookup_rates',destination='fixture://test',source_token='test',arguments=t.view.model_dump(mode='json'))
    monkeypatch.setattr(work,'request_tool',permit)
    async def slow(request):
        return await perform(request,mcp_module='services.slow_rates_mcp',budget_seconds=2)
    monkeypatch.setattr(module,'perform',slow)
    request=task()
    started=perf_counter()
    with TestClient(module.app) as client:
        response=client.post('/',json={'jsonrpc':'2.0','id':'timeout','method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':request.model_dump_json()}]}}})
    elapsed=perf_counter()-started
    assert response.status_code==200
    assert '"error_code":"timeout"' in response.text.replace('\\"','"')
    assert '"evidence":null' in response.text.replace('\\"','"')
    assert 1.8 <= elapsed < 8
    assert not module.task_store.tasks
    assert not asyncio.run(module.session_service.list_sessions(app_name='markets_demo')).sessions


def test_same_process_recovers_after_timeout(monkeypatch):
    from fastapi.testclient import TestClient
    import json
    import services.market_agent as module
    calls=0
    async def work(request):
        nonlocal calls
        calls+=1
        if calls==1:raise TimeoutError()
        return MarketResult(correlation_id=request.correlation_id,status='completed',evidence=lookup_rates(**request.view.model_dump()),summary='Simulazione',limits=[],model='test')
    monkeypatch.setattr(module,'perform',work)
    results=[]
    with TestClient(module.app) as client:
        for _ in range(2):
            request=task()
            response=client.post('/',json={'jsonrpc':'2.0','id':uuid4().hex,'method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':request.model_dump_json()}]}}})
            data=response.json()['result']
            parts=data.get('parts',[])+[p for a in data.get('artifacts',[]) for p in a['parts']]
            results.append(json.loads(next(p['text'] for p in parts if p['kind']=='text')))
            assert not module.task_store.tasks
            assert not asyncio.run(module.session_service.list_sessions(app_name='markets_demo')).sessions
    assert results[0]['error_code']=='timeout'
    assert results[1]['status']=='completed'
    assert results[0]['measurements']['agent_boot_id']==results[1]['measurements']['agent_boot_id']
