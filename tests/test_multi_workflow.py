import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from gateway.app import create_app
from gateway.agent_contracts import MarketResult,RateEvidence,TaxResult,TaxView
import gateway.market_client as markets
import gateway.tax_client as tax
from gateway.tax_evidence import expected_evidence as fixture_evidence
from gateway.agent_contracts import TaxView

def lookup_tax(**arguments):
    return fixture_evidence(TaxView(**arguments)).model_dump(mode="json")



@pytest.mark.parametrize('case,scenarios,expected,called',[
 ('C001',['S-01','S-02'],'completed',{'S-01','S-02'}),
 ('C001',['S-01'],'completed',{'S-01'}),
 ('C001',['S-02'],'completed',{'S-02'}),
 ('C006',['S-01','S-02'],'partial',{'S-02'}),
 ('C011',['S-01','S-02'],'partial',{'S-01'}),
 ('C016',['S-01','S-02'],'partial',{'S-02'}),
])
def test_requested_activities_and_partial(monkeypatch,case,scenarios,expected,called):
    received=[]
    async def market(task):
        received.append('S-01')
        return MarketResult(correlation_id=task.correlation_id,status='completed',evidence=RateEvidence(annual_rate_percent='3.20'),summary='Demo',limits=[],model='test')
    async def fiscal(task):
        received.append('S-02')
        payload=task.view.model_dump()
        assert set(payload)=={'tax_year','expense_category','purpose'}
        return TaxResult(correlation_id=task.correlation_id,status='completed',evidence=lookup_tax(**payload),summary='Demo',limits=[],model='test')
    monkeypatch.setattr(markets,'delegate',market);monkeypatch.setattr(tax,'delegate',fiscal)
    with TestClient(create_app()) as c:
        sid=c.post('/sessions/pdf',files=[('files',(kind+'.pdf',Path('dataset/Documents',case+'_'+kind+'.pdf').read_bytes())) for kind in ['mutuo','interessi']],data={'scenarios':scenarios}).json()['session_id']
        r=c.post(f'/sessions/{sid}/analysis')
        assert r.status_code==200,r.text
        assert r.json()['status']==expected
        assert set(received)==called
        assert set(r.json()['activities'])==set(scenarios)
        assert c.delete(f'/sessions/{sid}').status_code==404


def test_failure_one_branch_preserves_other(monkeypatch):
    async def fail(task):raise ConnectionError()
    async def fiscal(task):return TaxResult(correlation_id=task.correlation_id,status='completed',evidence=lookup_tax(**task.view.model_dump()),summary='Demo',limits=[],model='test')
    monkeypatch.setattr(markets,'delegate',fail);monkeypatch.setattr(tax,'delegate',fiscal)
    import json
    with TestClient(create_app()) as c:
        sid=c.post('/sessions',json=json.loads(Path('examples/session_complete.json').read_text())).json()['session_id']
        r=c.post(f'/sessions/{sid}/analysis').json()
        assert r['status']=='partial'
        assert r['activities']['S-01']['error_code']=='delegation_failed'
        assert r['activities']['S-02']['status']=='completed'
        assert r['session_closed']


def test_tax_contract_rejects_exact_amount():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):TaxView(tax_year=2025,purpose='renovation',annual_interest=1000)


def test_renovation_preserved_in_pdf():
    from gateway.pdf_input import extract_profile
    profile,_=extract_profile([Path('dataset/Documents/C024_interessi.pdf').read_bytes()])
    assert profile.purpose.value=='renovation'


def test_tax_a2a_cleanup(monkeypatch):
    import json
    from datetime import datetime,timedelta,timezone
    from uuid import uuid4
    from gateway.agent_contracts import TaxTask
    import services.tax_agent as module
    async def perform(task):return TaxResult(correlation_id=task.correlation_id,status='completed',evidence=lookup_tax(**task.view.model_dump()),summary='Demo',limits=[],model='test')
    monkeypatch.setattr(module,'perform',perform)
    task=TaxTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'tax_year':2024,'purpose':'renovation'})
    with TestClient(module.app) as c:
        response=c.post('/',json={'jsonrpc':'2.0','id':'test','method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':task.model_dump_json()}]}}})
        assert response.status_code==200
        assert 'error' not in response.json()
    assert not module.task_store.tasks
    assert not asyncio.run(module.session_service.list_sessions(app_name='tax_demo')).sessions


def test_parallel_execution_and_tax_timeout():
    from gateway.multi_workflow import run_analysis
    entered=set()
    async def exercise():
        both=asyncio.Event()
        async def delegate(task):
            entered.add(task.scenario)
            if len(entered)==2:both.set()
            await asyncio.wait_for(both.wait(),1)
            if task.scenario=='S-02':raise TimeoutError()
            return MarketResult(correlation_id=task.correlation_id,status='completed',evidence=RateEvidence(annual_rate_percent='3.20'),summary='Demo',limits=[],model='test')
        def view(s):return {'data':{'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}} if s=='S-01' else {'tax_year':2024,'purpose':'renovation'}}
        cleared=[]
        result=await run_analysis(['S-01','S-02'],view,{'S-01':delegate,'S-02':delegate},lambda:cleared.append(True))
        assert result['status']=='partial'
        assert result['activities']['S-02']['error_code']=='timeout'
        assert cleared==[True]
    asyncio.run(exercise())
