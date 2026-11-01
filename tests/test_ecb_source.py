"""Fonte reale con risposta pubblica congelata; suite offline, nessuna rete BCE."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from gateway.ecb_source import (EcbRateEvidence, SOURCE_URL, SOURCE_ID, SERIES_KEY, BRIDGE_JOB,
    REAL_MARKET_PROMPT, PublicObservation, parse_csv, verify_ecb, fetch_ecb, public_prompt_data)
from gateway.agent_contracts import MarketTask, MarketResult, MarketEvidence
from gateway.inference import InferenceBroker, InferenceRequest
from gateway.a2a_egress import EgressDenied
from gateway.result_validation import MissingProvenanceError


def snapshot():
    return json.loads(Path('tests/fixtures/ecb_mir_public_response.json').read_text())


def evidence():
    data=snapshot();row=parse_csv(data['source_csv'])
    return EcbRateEvidence(annual_rate_percent=row['OBS_VALUE'],observation_period=row['TIME_PERIOD'],
        source_csv=data['source_csv'],retrieved_at=data['retrieved_at'],response_sha256=data['response_sha256'])


def task():
    return MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),
        view={'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})


def test_snapshot_value_period_and_digest_are_replayed():
    data=evidence();checked,digest=verify_ecb(data.model_dump(mode='json'))
    assert checked==data and len(digest)==64
    assert hashlib.sha256(data.source_csv.encode()).hexdigest()==data.response_sha256
    assert MarketEvidence.model_validate(data.model_dump(mode='json'))==data
    assert not hasattr(data,'reference_date')  # Nessun giorno inventato da un periodo mensile.


@pytest.mark.parametrize('field',['source_id','retrieved_at','source_csv','response_sha256','source_url','measure'])
def test_missing_provenance_not_filled_by_defaults(field):
    data=evidence().model_dump(mode='json');del data[field]
    with pytest.raises((MissingProvenanceError,ValueError)):verify_ecb(data)


@pytest.mark.parametrize('change',['rate','period','digest','unit','url','series','future_period','timezone'])
def test_altered_metadata_or_value_rejected(change):
    data=evidence().model_dump(mode='json')
    if change=='rate':data['annual_rate_percent']='9.99'
    if change=='period':data['observation_period']='2000-01'
    if change=='digest':data['response_sha256']='0'*64
    if change=='unit':data['unit']='percent_per_month'
    if change=='url':data['source_url']='https://example.invalid/'
    if change=='series':data['series_key']='other'
    if change=='future_period':data['retrieved_at']='2000-01-01T00:00:00Z'
    if change=='timezone':data['retrieved_at']='2026-10-31T00:00:00'
    with pytest.raises(ValueError):verify_ecb(data)


@pytest.mark.parametrize('change',['two_rows','wrong_country','wrong_unit','missing_value','duplicate_headers','private','estimate','oversized'])
def test_csv_invalid_or_out_of_scope_rejected(change):
    content=snapshot()['source_csv']
    if change=='two_rows':content+=content.splitlines()[-1]+'\r\n'
    if change=='wrong_country':content=content.replace(',IT,',',FR,')
    if change=='wrong_unit':content=content.replace(',PCPA,',',EUR,')
    if change=='missing_value':content=content.replace(',3.55,',',,')
    if change=='duplicate_headers':content=content.replace('FREQ,REF_AREA','KEY,REF_AREA')
    if change=='private':content=content.replace(',A,F,',',A,C,')
    if change=='estimate':content=content.replace(',A,F,',',E,F,')
    if change=='oversized':content+='x'*17000
    with pytest.raises((ValueError,KeyError)):
        row=parse_csv(content)
        EcbRateEvidence(annual_rate_percent=row['OBS_VALUE'],observation_period=row['TIME_PERIOD'])


@pytest.mark.parametrize('fault',[None,'redirect','unavailable','html','encoding','oversized','timeout'])
def test_http_exact_request_and_fail_closed(monkeypatch,fault):
    calls=[];original=httpx.AsyncClient
    def receive(req):
        calls.append(req)
        assert str(req.url)==SOURCE_URL and req.method=='GET' and not req.content
        assert 'authorization' not in req.headers and 'x-tesi-service-key' not in req.headers and 'cookie' not in req.headers
        if fault=='timeout':raise httpx.ReadTimeout('private exception')
        return httpx.Response(302 if fault=='redirect' else 503 if fault=='unavailable' else 200,
            headers={'content-type':'text/html' if fault=='html' else 'text/csv',
                     'content-encoding':'opaque' if fault=='encoding' else 'identity',
                     'location':'https://example.invalid/'},
            content=(b'x'*17000 if fault=='oversized' else snapshot()['source_csv'].encode()))
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
    if fault:
        with pytest.raises((ValueError,httpx.HTTPError)):asyncio.run(fetch_ecb())
    else:
        data,ms=asyncio.run(fetch_ecb());assert data.source_id==SOURCE_ID and ms>=0
    assert len(calls)==1


class FakeBridge:
    def __init__(self):self.model_calls=0
    def revoke(self,owner):pass
    async def infer(self,payload,seconds,*,owner=None):
        if payload==BRIDGE_JOB:return {'body':evidence().model_dump(mode='json'),'ollama_ms':None,'source_ms':1}
        self.model_calls+=1
        assert payload['messages'][0]['content']==REAL_MARKET_PROMPT
        projected=json.loads(payload['messages'][1]['content'])
        assert 'source_csv' not in projected and 'retrieved_at' not in projected
        assert set(projected)==set(PublicObservation.model_fields)
        return {'body':{'message':{'content':'Sintesi non verificata'},'prompt_eval_count':1,'eval_count':1,'load_duration':0},'ollama_ms':1}


@pytest.mark.parametrize('fault',[None,'no_fetch','changed_return','changed_for_model'])
def test_gateway_attests_actual_receipt_not_agent_claims(monkeypatch,fault):
    import gateway.tool_egress as tools
    from gateway import runtime
    monkeypatch.setattr(runtime,'ISOLATED',True);monkeypatch.setattr(runtime,'MODE','isolated')
    monkeypatch.setattr(tools,'MARKET_SOURCE','ecb')
    routes=dict(tools.TOOL_ROUTES);routes['S-01']=replace(routes['S-01'],destination='ecb://mir-it-house-purchase-v1')
    monkeypatch.setattr(tools,'TOOL_ROUTES',routes)
    broker=InferenceBroker();broker.bridge=FakeBridge()
    async def remote(t):
        raw=evidence().model_dump(mode='json')
        if fault!='no_fetch':
            request=tools.ToolRequest(correlation_id=t.correlation_id,scenario=t.scenario,tool='lookup_rates',arguments=t.view.model_dump(mode='json'))
            permit=tools.authorize_tool(broker,request,'Bearer '+t.inference_token)
            raw=await tools.source_request(broker,tools.SourceRequest(**request.model_dump(),destination=permit.destination,headers={}), 'Bearer '+permit.source_token)
        if fault in ('changed_return','changed_for_model'):
            raw=deepcopy(raw);raw['annual_rate_percent']='3.56';raw['source_csv']=raw['source_csv'].replace(',3.55,',',3.56,')
            raw['response_sha256']=hashlib.sha256(raw['source_csv'].encode()).hexdigest()
            verify_ecb(raw)  # Auto-coerenza e hash non sono prova di origine.
        if fault in (None,'changed_for_model'):
            await broker.infer(InferenceRequest(correlation_id=t.correlation_id,scenario=t.scenario,evidence=raw),'Bearer '+t.inference_token)
        return MarketResult(correlation_id=t.correlation_id,status='completed',evidence=MarketEvidence.model_validate(raw),summary='Demo',limits=[],model='test')
    if fault:
        with pytest.raises(EgressDenied):asyncio.run(broker.delegate(uuid4(),task(),remote))
        assert broker.bridge.model_calls==0
    else:
        result=asyncio.run(broker.delegate(uuid4(),task(),remote))
        assert result.measurements['gateway_source_receipt_verified']==1
        assert result.measurements['external_http_requests']==1 and broker.bridge.model_calls==1
    assert not broker._grants


def test_real_report_context_is_separate_and_not_used_as_nominal_rate():
    from gateway.pdf_input import extract_profile
    from gateway.report import build_report
    from gateway.report_document import render_report_document
    profile,_=extract_profile([Path('dataset/Documents/C001_mutuo.pdf').read_bytes()])
    result={'evidence':evidence().model_dump(mode='json'),'summary':'Non pubblicare','model':'test','limits':[], 'measurements':{'gateway_source_receipt_verified':1}}
    activities={'S-01':{'status':'completed','error_code':None,'result':result}}
    report=build_report(profile,['S-01'],activities,'completed')
    assert not report['simulated_sources'] and len(report['external_sources'])==1
    assert report['mortgage_comparison']['reason']=='incompatible_market_measure'
    assert report['mortgage_comparison']['assumptions']==[]
    assert all('simulat' not in note.lower() for note in report['mortgage_comparison']['limits'])
    assert report['mortgage_comparison']['documented_monthly_payment']==str(profile.payment_amount.value)
    assert report['consistency']['comparisons'][0]['status']=='not_comparable'
    html=render_report_document(report)
    assert 'AAR/NDER' in html and evidence().observation_period in html and SOURCE_URL.replace('&','&amp;') in html
    result['measurements']['gateway_source_receipt_verified']=0
    with pytest.raises(ValueError):build_report(profile,['S-01'],activities,'completed')


def test_source_job_does_not_use_inference_metrics():
    from gateway.ollama_bridge import OllamaBridge
    async def run():
        bridge=OllamaBridge();pending=asyncio.create_task(bridge.infer(BRIDGE_JOB,1));job=await bridge.poll()
        assert bridge.kind(job['job_id'])=='ecb_market_source'
        assert bridge.complete(job['job_id'],body={'ok':True},source_ms=1)
        reply=await pending;assert reply['ollama_ms'] is None and reply['source_ms']==1
    asyncio.run(run())


@pytest.mark.parametrize('variant',['disabled','extra_url','unknown_kind','enabled'])
def test_host_bridge_opt_in_and_exact_template(monkeypatch,variant):
    import scripts.run_ollama_bridge as bridge
    called=[]
    async def fake_fetch():called.append(True);return evidence(),1
    monkeypatch.setattr(bridge,'fetch_ecb',fake_fetch)
    payload=dict(BRIDGE_JOB)
    if variant=='extra_url':payload['url']='https://example.invalid/'
    if variant=='unknown_kind':payload['kind']='arbitrary_http'
    if variant=='enabled':
        result=asyncio.run(bridge.execute_payload(payload,None,True))
        assert result[0]['source_id']==SOURCE_ID and result[1] is None and result[2]==1
        assert len(called)==1
    else:
        with pytest.raises(ValueError):asyncio.run(bridge.execute_payload(payload,None,variant!='disabled'))
        assert not called


def test_real_model_projection_prompt_is_explicit_and_bounded():
    from scripts.run_ollama_bridge import validate_payload
    from gateway.inference import MODELS
    projected=public_prompt_data(evidence())
    payload={'model':MODELS['S-01'],'stream':False,'keep_alive':0,
        'options':{'num_ctx':4096,'num_predict':200,'temperature':0},
        'messages':[{'role':'system','content':REAL_MARKET_PROMPT},{'role':'user','content':json.dumps(projected)}]}
    assert validate_payload(payload)==payload
    projected['source_csv']='untrusted text'
    payload['messages'][1]['content']=json.dumps(projected)
    with pytest.raises(ValueError):validate_payload(payload)
