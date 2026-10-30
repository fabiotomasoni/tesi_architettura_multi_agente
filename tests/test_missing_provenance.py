import json,asyncio
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timedelta,timezone
import pytest
from gateway.result_validation import parse_result
from gateway.agent_contracts import MarketTask,MarketResult,RateEvidence,TaxTask,TaxResult,TaxEvidence
from gateway.tax_evidence import expected_evidence
from gateway.report import build_report
from gateway.models import SessionInput


def task(fiscal=False):
    return (TaxTask if fiscal else MarketTask)(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'tax_year':2025,'purpose':'primary_home_purchase'} if fiscal else {'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})


@pytest.mark.parametrize('fiscal',[False,True])
@pytest.mark.parametrize('missing',['evidence','source_id'])
def test_missing_provenance_sanitized(fiscal,missing):
    t=task(fiscal);evidence=expected_evidence(t.view).model_dump() if fiscal else RateEvidence(annual_rate_percent='3.20').model_dump()
    if missing=='source_id':del evidence['source_id']
    else:evidence=None
    raw={'correlation_id':str(t.correlation_id),'status':'completed','evidence':evidence,'summary':'spetta sempre','limits':[],'model':'test'}
    parsed=parse_result(json.dumps(raw),t,TaxResult if fiscal else MarketResult,TaxEvidence if fiscal else RateEvidence,('source_id','reference') if fiscal else ('source_id','reference_date','unit','simulated'))
    assert parsed.status=='unverified' and parsed.error_code=='missing_provenance'
    assert parsed.evidence is None
    assert 'spetta' not in parsed.model_dump_json()


def test_malformed_content_not_relabeled_missing_provenance():
    t=task()
    with pytest.raises(ValueError):parse_result(json.dumps({'correlation_id':str(t.correlation_id),'status':'completed','evidence':{'annual_rate_percent':'invalid'},'summary':'x','model':'test','limits':[]}),t,MarketResult,RateEvidence,('source_id',))


def test_unverified_report_has_no_source_summary_or_calculation():
    p=SessionInput.model_validate(json.loads(Path('examples/session_complete.json').read_text())).profile
    t=task();r=MarketResult(correlation_id=t.correlation_id,status='unverified',error_code='missing_provenance',summary='Escluso',limits=['Provenienza mancante'],model='test')
    report=build_report(p,['S-01'],{'S-01':{'status':'unverified','error_code':'missing_provenance','result':r.model_dump(mode='json')}},'unverified')
    assert not report['simulated_sources'] and not report['faithful_summaries']
    assert report['mortgage_comparison']['status']=='not_calculated'
    assert report['outcomes'][0]['status']=='unverified'


def test_unverified_branch_preserves_completed_and_finalizes():
    from gateway.multi_workflow import run_analysis
    cleared=[]
    def view(s):return {'data':{'tax_year':2025,'purpose':'primary_home_purchase'} if s=='S-02' else {'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}}}
    async def delegate(t):
        if t.scenario=='S-01':return MarketResult(correlation_id=t.correlation_id,status='unverified',error_code='missing_provenance',summary='Escluso',limits=[],model='test')
        return TaxResult(correlation_id=t.correlation_id,status='completed',evidence=expected_evidence(t.view),summary='Demo',limits=[],model='test')
    result=asyncio.run(run_analysis(['S-01','S-02'],view,{'S-01':delegate,'S-02':delegate},lambda:cleared.append(True)))
    assert result['status']=='partial' and result['activities']['S-01']['status']=='unverified'
    assert result['activities']['S-02']['status']=='completed' and cleared==[True]


def test_api_unverified_only_report_and_cleanup(monkeypatch):
    from fastapi.testclient import TestClient
    from gateway.app import create_app
    import gateway.market_client as remote
    async def delegate(t):
        raw={'correlation_id':str(t.correlation_id),'status':'completed','evidence':None,'summary':'Conclusione inventata','limits':[],'model':'fixture'}
        return parse_result(json.dumps(raw),t,MarketResult,RateEvidence,('source_id','reference_date','unit','simulated'))
    monkeypatch.setattr(remote,'delegate',delegate)
    payload=json.loads(Path('examples/session_complete.json').read_text());payload['scenarios']=['S-01']
    with TestClient(create_app()) as c:
        sid=c.post('/sessions',json=payload).json()['session_id']
        response=c.post(f'/sessions/{sid}/analysis')
        assert response.status_code==200
        result=response.json()
        assert result['status']=='unverified'
        assert result['report']['mortgage_comparison']['status']=='not_calculated'
        assert result['report']['simulated_sources']==[]
        assert 'Conclusione inventata' not in response.text
        assert result['session_closed'] and c.delete(f'/sessions/{sid}').status_code==404


def test_fixture_emits_incomplete_result_over_a2a(monkeypatch):
    from fastapi.testclient import TestClient
    import services.market_agent as module
    async def missing(t):return MarketResult.model_construct(correlation_id=t.correlation_id,status='completed',evidence=None,summary='Escludere',limits=[],model='fixture',measurements={})
    monkeypatch.setattr(module,'perform',missing)
    t=task()
    with TestClient(module.app) as c:
        response=c.post('/',json={'jsonrpc':'2.0','id':'missing','method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':t.model_dump_json()}]}}})
        result=response.json()['result']
        parts=result.get('parts',[])+[p for a in result.get('artifacts',[]) for p in a['parts']]
        text=next(p['text'] for p in parts if p['kind']=='text')
        assert parse_result(text,t,MarketResult,RateEvidence,('source_id',)).status=='unverified'
    assert not module.task_store.tasks


@pytest.mark.parametrize('fiscal',[False,True])
def test_mcp_catalog_does_not_restore_omitted_provenance(fiscal):
    from gateway.result_validation import MissingProvenanceError
    from gateway.market_evidence import verify_evidence as market_verify
    from gateway.tax_evidence import verify_evidence as tax_verify
    t=task(fiscal)
    evidence=expected_evidence(t.view).model_dump() if fiscal else RateEvidence(annual_rate_percent='3.20').model_dump()
    del evidence['source_id']
    with pytest.raises(MissingProvenanceError):(tax_verify if fiscal else market_verify)(evidence,t.view)


@pytest.mark.parametrize('fiscal',[False,True])
def test_agent_mcp_missing_provenance_becomes_unverified(monkeypatch,fiscal):
    from fastapi.testclient import TestClient
    from gateway.result_validation import MissingProvenanceError
    if fiscal:import services.tax_agent as module
    else:import services.market_agent as module
    async def perform(t):raise MissingProvenanceError('missing source_id')
    monkeypatch.setattr(module,'perform',perform)
    t=task(fiscal)
    with TestClient(module.app) as c:
        response=c.post('/',json={'jsonrpc':'2.0','id':'mcp-source','method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':t.model_dump_json()}]}}})
        result=response.json()['result'];parts=result.get('parts',[])+[p for a in result.get('artifacts',[]) for p in a['parts']]
        parsed=json.loads(next(p['text'] for p in parts if p['kind']=='text'))
        assert parsed['status']=='unverified' and parsed['error_code']=='missing_provenance'
        assert parsed['evidence'] is None
    assert not module.task_store.tasks


@pytest.mark.parametrize('fiscal',[False,True])
def test_real_mcp_missing_source_stops_before_ollama(monkeypatch,fiscal):
    from gateway.result_validation import MissingProvenanceError
    if fiscal:import services.tax_work as work
    else:import services.market_work as work
    def forbidden(*args,**kwargs):pytest.fail('Ollama non deve essere chiamato senza fonte MCP')
    monkeypatch.setattr(work.httpx,'AsyncClient',forbidden)
    with pytest.raises(MissingProvenanceError):asyncio.run(work.perform(task(fiscal),mcp_module='services.missing_source_mcp'))
