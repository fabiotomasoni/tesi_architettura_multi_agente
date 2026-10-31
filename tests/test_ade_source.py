"""Catalogo fiscale reale: regressioni offline e recupero HTTP simulato controllato."""
import asyncio
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
from uuid import uuid4
import hashlib
import httpx
import pytest
from gateway import ade_source as ade
from gateway.agent_contracts import TaxView,TaxTask,TaxResult
from gateway.tax_evidence import verify_evidence,faithful_summary
from gateway.tax_publications import PUBLICATIONS


def evidence(year=2025,purpose='primary_home_purchase'):
    p=ade.publication(year)
    return ade.AdeEvidence(source_id='ade-annual-mortgage-v1',simulated=False,**p|{'quotes':ade.selected_quotes(year,purpose),'purpose':purpose,'retrieved_at':datetime.now(timezone.utc)})


@pytest.mark.parametrize('year',[2024,2025])
@pytest.mark.parametrize('purpose',['primary_home_purchase','renovation','primary_home_construction','other'])
def test_catalog_context_quotes_and_model_projection(year,purpose):
    e=evidence(year,purpose);checked,digest=verify_evidence(e,TaxView(tax_year=year,purpose=purpose))
    assert checked.publication_year==year+1 and len(digest)==64
    summary=faithful_summary(e,TaxView(tax_year=year,purpose=purpose))
    assert summary['simulated'] is False and 'spettanza' in summary['limit']
    assert all('#page=' in s['source_ref'] for s in summary['statements'])
    if purpose=='renovation':assert not any('Rigo E7' in q['text'] for q in e.quotes)
    data=ade.prompt_data(e)
    assert not {'purpose','source_url','retrieved_at','document_sha256'} & data.keys()
    from gateway.inference import MODELS
    from scripts.run_ollama_bridge import validate_payload
    import json
    payload={'model':MODELS['S-02'],'stream':False,'keep_alive':0,'options':{'num_ctx':4096,'num_predict':200,'temperature':0},'think':False,'messages':[{'role':'system','content':ade.REAL_TAX_PROMPT},{'role':'user','content':json.dumps(data)}]}
    assert validate_payload(payload)==payload


@pytest.mark.parametrize('field,value',[('tax_year',2023),('publication_year',2024),('source_url','https://example.org'),('document_sha256','0'*64),('quotes',[{'page':1,'text':'detrazione certa'}]),('retrieved_at','2025-01-01T00:00:00')])
def test_tampered_evidence_rejected(field,value):
    raw=evidence().model_dump(mode='json');raw[field]=value
    with pytest.raises(ValueError):verify_evidence(raw,TaxView(tax_year=2025,purpose='primary_home_purchase'))


@pytest.mark.parametrize('fault',['ok','redirect','html','changed','oversize','timeout'])
def test_bounded_fixed_https_fetch(monkeypatch,fault):
    raw=b'%PDF-fixture';p=deepcopy(PUBLICATIONS['2025']);p['document_sha256']=hashlib.sha256(raw).hexdigest()
    monkeypatch.setitem(PUBLICATIONS,'2025',p);requests=[];original=httpx.AsyncClient
    def receive(req):
        requests.append(req)
        assert str(req.url)==p['source_url'] and req.method=='GET' and not req.content
        assert 'authorization' not in req.headers and 'cookie' not in req.headers
        if fault=='timeout':raise httpx.ReadTimeout('timeout')
        return httpx.Response(302 if fault=='redirect' else 200,headers={'content-type':'text/html' if fault=='html' else 'application/pdf'},content=b'%PDF-changed' if fault=='changed' else b'x'*(ade.MAX_BYTES+1) if fault=='oversize' else raw)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
    if fault=='ok':
        data,ms=asyncio.run(ade.fetch_ade(2025));assert data['document_sha256']==p['document_sha256'] and ms>=0
    else:
        with pytest.raises((ValueError,httpx.HTTPError)):asyncio.run(ade.fetch_ade(2025))
    assert len(requests)==1


def test_bridge_opt_in_and_no_caller_url(monkeypatch):
    from scripts import run_ollama_bridge as bridge
    calls=[]
    async def fetch(year):calls.append(year);return {'public':True},1
    monkeypatch.setattr(bridge,'fetch_ade',fetch)
    with pytest.raises(ValueError):asyncio.run(bridge.execute_payload(ade.source_job(2025),None))
    with pytest.raises(ValueError):asyncio.run(bridge.execute_payload({**ade.source_job(2025),'url':'https://example.org'},None,enable_ade=True))
    with pytest.raises(ValueError):ade.source_job(2023)
    assert not calls
    assert asyncio.run(bridge.execute_payload(ade.source_job(2025),None,enable_ade=True))[2]==1
    assert calls==[2025]


@pytest.mark.parametrize('receipt',[0,1])
def test_real_tax_report_requires_receipt_and_no_fiscal_entitlement(receipt):
    from gateway.pdf_input import extract_profile
    from gateway.report import build_report
    from gateway.report_document import render_report_document
    p,_=extract_profile([Path('dataset/Documents/C001_interessi.pdf').read_bytes()])
    e=evidence(int(str(p.tax_year.value)),p.purpose.value)
    a={'S-02':{'status':'completed','result':{'evidence':e.model_dump(mode='json'),'summary':'Detrazione garantita inventata','model':'test','measurements':{'gateway_source_receipt_verified':receipt}}}}
    if not receipt:
        with pytest.raises(ValueError):build_report(p,['S-02'],a,'completed')
        return
    report=build_report(p,['S-02'],a,'completed');html=render_report_document(report)
    assert len(report['external_sources'])==1 and not report['simulated_sources']
    tax=report['tax_application'];assert not tax['deduction_calculated'] and tax['tax_entitlement']=='not_assessed'
    assert tax['source']['simulated'] is False
    assert not any('Fonte simulata' in t for t in tax['limits'])
    assert 'Detrazione garantita inventata' not in html and 'Agenzia delle Entrate' in html
    assert 'BCE / Eurosistema' not in html


@pytest.mark.parametrize('fault',[None,'no_fetch','changed_return','changed_prompt'])
def test_gateway_attests_publication_receipt(monkeypatch,fault):
    from dataclasses import replace
    from gateway import runtime
    import gateway.tool_egress as tools
    from gateway.inference import InferenceBroker,InferenceRequest
    from gateway.a2a_egress import EgressDenied
    monkeypatch.setattr(runtime,'ISOLATED',True)
    monkeypatch.setattr(tools,'TAX_SOURCE','ade')
    routes=dict(tools.TOOL_ROUTES);routes['S-02']=replace(routes['S-02'],destination=ade.DESTINATION)
    monkeypatch.setattr(tools,'TOOL_ROUTES',routes)
    class Bridge:
        model_calls=0
        async def infer(self,payload,seconds):
            if payload.get('kind')=='ade_tax_source':
                return {'body':{**ade.publication(2025),'retrieved_at':datetime.now(timezone.utc).isoformat()},'source_ms':1}
            self.model_calls+=1
            return {'body':{'message':{'content':'Test'},'prompt_eval_count':1,'eval_count':1,'load_duration':0},'ollama_ms':1}
    broker=InferenceBroker();broker.bridge=Bridge()
    from gateway.privacy import SensitiveContext
    session_id=uuid4()
    from decimal import Decimal
    broker._privacy[session_id]=SensitiveContext(entities={'riva','via'},amounts={Decimal('61'),Decimal('64'),Decimal('2025')})
    t=TaxTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view=TaxView(tax_year=2025,purpose='renovation'))
    async def remote(task):
        raw=evidence(2025,'renovation').model_dump(mode='json')
        if fault!='no_fetch':
            request=tools.ToolRequest(correlation_id=task.correlation_id,scenario='S-02',tool='lookup_tax',arguments=task.view.model_dump(mode='json'))
            permit=tools.authorize_tool(broker,request,'Bearer '+task.inference_token)
            raw=await tools.source_request(broker,tools.SourceRequest(**request.model_dump(),destination=permit.destination,headers={}), 'Bearer '+permit.source_token)
        if fault in {'changed_return','changed_prompt'}:
            raw['retrieved_at']='2026-01-01T00:00:00Z'
        if fault in {None,'changed_prompt'}:
            await broker.infer(InferenceRequest(correlation_id=task.correlation_id,scenario='S-02',evidence=raw),'Bearer '+task.inference_token)
        return TaxResult(correlation_id=task.correlation_id,status='completed',evidence=raw,summary='Test',limits=[],model='test')
    if fault:
        with pytest.raises(EgressDenied):asyncio.run(broker.delegate(session_id,t,remote))
        assert broker.bridge.model_calls==0
    else:
        r=asyncio.run(broker.delegate(session_id,t,remote));assert r.measurements['gateway_source_receipt_verified']==1 and r.measurements['external_http_requests']==1
    assert not broker._grants


def test_tax_checker_direct_cli_matches_module_invocation(tmp_path):
    import json,subprocess,sys
    from gateway.pdf_input import extract_profile
    from gateway.report import build_report
    profile,_=extract_profile([Path('dataset/Documents/C001_interessi.pdf').read_bytes()])
    e=evidence(int(str(profile.tax_year.value)),profile.purpose.value)
    activity={'S-02':{'status':'completed','result':{'evidence':e.model_dump(mode='json'),'summary':'test','model':'test','measurements':{'gateway_source_receipt_verified':1}}}}
    report=build_report(profile,['S-02'],activity,'completed')
    path=tmp_path/'report.json';path.write_text(json.dumps(report))
    direct=subprocess.run([sys.executable,'scripts/check_tax_application.py',str(path)],capture_output=True,text=True)
    module=subprocess.run([sys.executable,'-m','scripts.check_tax_application',str(path)],capture_output=True,text=True)
    assert direct.returncode==0,direct.stderr
    assert module.returncode==0,module.stderr
    assert direct.stdout==module.stdout
    assert 'official_source_checked: True' in direct.stdout
