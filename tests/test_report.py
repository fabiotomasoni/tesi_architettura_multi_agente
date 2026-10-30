import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from gateway.app import create_app
from gateway.models import SessionInput
from gateway.report import build_report
from gateway.agent_contracts import MarketResult,RateEvidence
import gateway.market_client as remote


def payload():return json.loads(Path('examples/session_complete.json').read_text())


def test_report_separates_documents_fixture_and_unverified_summary():
    profile=SessionInput.model_validate(payload()).profile
    activity={'status':'completed','error_code':None,'result':{'evidence':{'simulated':True,'source_id':'simulated-rates-v1','annual_rate_percent':'3.20','reference_date':'2025-12-31','unit':'percent_per_year'},'summary':'Testo modello','model':'test','limits':[]}}
    report=build_report(profile,['S-01'],{'S-01':activity},'completed')
    assert report['document_data'][0]['facts']['remaining_principal']['source']['page']==1
    assert report['simulated_sources'][0]['real_world_verified'] is False
    assert report['unverified_summaries']==[]
    assert report['faithful_summaries'][0]['verification']=='faithful_to_authorized_fixture'
    assert report['model_evaluation'][0]['free_text_included'] is False
    assert report['requested_scenarios']==['S-01']


def test_report_blocked_marks_missing_and_does_not_invent_sources():
    profile=SessionInput.model_validate(payload()).profile
    profile.remaining_principal=None
    report=build_report(profile,['S-01'],{'S-01':{'status':'blocked','error_code':'input_not_ready'}},'blocked')
    assert report['document_data'][0]['facts']['remaining_principal']['status']=='missing'
    assert report['simulated_sources']==[]
    assert report['unverified_summaries']==[]


def test_api_builds_report_before_session_cleanup(monkeypatch):
    async def delegate(task):return MarketResult(correlation_id=task.correlation_id,status='completed',evidence=RateEvidence(annual_rate_percent='3.20'),summary='Demo',limits=[],model='test')
    monkeypatch.setattr(remote,'delegate',delegate)
    with TestClient(create_app()) as c:
        data=payload();data['scenarios']=['S-01']
        sid=c.post('/sessions',json=data).json()['session_id']
        r=c.post(f'/sessions/{sid}/analysis').json()
        assert r['report']['status']=='completed'
        assert r['report_ms']>=0
        assert c.delete(f'/sessions/{sid}').status_code==404


def test_report_failure_still_finalizes():
    import asyncio
    from gateway.multi_workflow import run_analysis
    from fastapi import HTTPException
    cleared=[]
    def view(s):raise HTTPException(409,'missing')
    def broken(*args):raise ValueError('report error')
    with pytest.raises(ValueError):asyncio.run(run_analysis(['S-01'],view,{'S-01':None},lambda:cleared.append(True),broken))
    assert cleared==[True]
