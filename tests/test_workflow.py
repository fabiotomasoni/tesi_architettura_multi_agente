import asyncio
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
from gateway.app import create_app
from gateway.agent_contracts import MarketResult, RateEvidence
import gateway.market_client as remote


@pytest.mark.parametrize('mode',['success','failed','exception','invalid'])
def test_workflow_result_and_automatic_cleanup(monkeypatch,mode):
    received=[]
    async def delegate(task):
        received.append(task)
        if mode=='exception':raise ConnectionError('secret')
        result=MarketResult(correlation_id=task.correlation_id,status='failed' if mode=='failed' else 'completed',error_code='timeout' if mode=='failed' else None,evidence=None if mode=='failed' else RateEvidence(annual_rate_percent='3.20'),summary='Simulazione',limits=[],model='test')
        if mode=='invalid':result=result.model_copy(update={'correlation_id':__import__('uuid').uuid4()})
        return result
    monkeypatch.setattr(remote,'delegate',delegate)
    with TestClient(create_app()) as c:
        payload=json.loads(Path('examples/session_complete.json').read_text())
        sid=c.post('/sessions',json=payload).json()['session_id']
        response=c.post(f'/sessions/{sid}/workflow')
        assert response.status_code==200,response.text
        result=response.json()
        assert result['status']==('completed' if mode=='success' else 'failed')
        assert result['session_closed']
        assert result['phases'][-1]['phase']=='cleanup'
        assert c.delete(f'/sessions/{sid}').status_code==404
        assert 'secret' not in response.text
        assert 'remaining_principal' not in received[0].model_dump_json()
        if mode=='invalid':assert 'result' not in result


def test_workflow_blocks_before_delegation_and_closes(monkeypatch):
    async def forbidden(*args):pytest.fail('Delega non autorizzata')
    monkeypatch.setattr(remote,'delegate',forbidden)
    with TestClient(create_app()) as c:
        payload=json.loads(Path('examples/session_missing.json').read_text())
        sid=c.post('/sessions',json=payload).json()['session_id']
        result=c.post(f'/sessions/{sid}/workflow').json()
        assert result['status']=='blocked'
        assert [p['phase'] for p in result['phases']]==['request_view','cleanup']
        assert c.delete(f'/sessions/{sid}').status_code==404


def test_workflow_cancellation_finalizes():
    from gateway.workflow import run_workflow
    cleared=[]
    def view():return {'data':{'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}}}
    async def exercise():
        entered=asyncio.Event()
        async def wait(task):
            entered.set()
            await asyncio.Event().wait()
        running=asyncio.create_task(run_workflow(view,wait,lambda:cleared.append(True)))
        await entered.wait()
        running.cancel()
        with pytest.raises(asyncio.CancelledError):await running
    asyncio.run(exercise())
    assert cleared==[True]
