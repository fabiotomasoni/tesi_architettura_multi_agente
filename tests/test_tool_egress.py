"""Confine MCP/fonti: dinieghi prima del trasporto e percorso completo locale."""
import asyncio
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway.a2a_egress import EgressDenied
from gateway.agent_contracts import MarketTask,TaxTask
from gateway.inference import InferenceBroker,OLLAMA_ENDPOINT
import gateway.tool_egress as tools


def task(fiscal=False):
    fields={'correlation_id':uuid4(),'deadline':datetime.now(timezone.utc)+timedelta(seconds=60)}
    if fiscal:return TaxTask(**fields,view={'tax_year':2025,'purpose':'renovation'})
    return MarketTask(**fields,view={'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})


def tool_request(t):
    return tools.ToolRequest(correlation_id=t.correlation_id,scenario=t.scenario,tool=tools.TOOL_ROUTES[t.scenario].tool,arguments=t.view.model_dump(mode='json'))


def source_request(t,permit):
    return tools.SourceRequest(**tool_request(t).model_dump(),destination=permit.destination,headers={})


@pytest.mark.parametrize('fiscal',[False,True])
def test_fixture_and_single_use(fiscal):
    broker=InferenceBroker()
    async def delegate(t):
        permit=tools.authorize_tool(broker,tool_request(t),'Bearer '+t.inference_token)
        with pytest.raises(EgressDenied):tools.authorize_tool(broker,tool_request(t),'Bearer '+t.inference_token)
        r=source_request(t,permit)
        result=await tools.source_request(broker,r,'Bearer '+permit.source_token)
        assert result['simulated'] is True
        with pytest.raises(EgressDenied):await tools.source_request(broker,r,'Bearer '+permit.source_token)
        return SimpleNamespace(measurements={})
    result=asyncio.run(broker.delegate(uuid4(),task(fiscal),delegate))
    assert result.measurements['gateway_tool_authorized']==1
    assert result.measurements['gateway_source_completed']==1
    assert not broker._grants


@pytest.mark.parametrize('fault',['tool','extra','changed','opaque','correlation','scenario','absent','expired','module'])
def test_tool_denials(fault):
    broker=InferenceBroker()
    async def delegate(t):
        r=tool_request(t);auth='Bearer '+t.inference_token
        if fault=='module':r.server_module='services.untrusted'
        if fault=='tool':r.tool='lookup_tax'
        if fault=='extra':r.arguments['remaining_principal']='secret'
        if fault=='changed':r.arguments['rate_type']='variable'
        if fault=='opaque':r.arguments={'body':'opaque'}
        if fault=='correlation':r.correlation_id=uuid4()
        if fault=='scenario':r.scenario='S-02'
        if fault=='absent':auth=None
        if fault=='expired':broker._grants[t.inference_token].task.deadline=datetime.now(timezone.utc)-timedelta(seconds=1)
        with pytest.raises(EgressDenied):tools.authorize_tool(broker,r,auth)
        assert not broker._grants[t.inference_token].tool_used
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(uuid4(),task(),delegate))


@pytest.mark.parametrize('fault',['url','query','path','header','body','tool','correlation','scenario','token','revoked'])
def test_source_denied_before_transport(monkeypatch,fault):
    def forbidden(**kwargs):pytest.fail('Trasporto chiamato prima del diniego')
    monkeypatch.setattr(httpx,'AsyncClient',forbidden)
    broker=InferenceBroker();sid=uuid4()
    async def delegate(t):
        permit=tools.authorize_tool(broker,tool_request(t),'Bearer '+t.inference_token)
        r=source_request(t,permit);auth='Bearer '+permit.source_token
        if fault=='url':r.destination='https://example.invalid/'
        if fault=='query':r.destination+='?name=secret'
        if fault=='path':r.destination+='/secret'
        if fault=='header':r.headers={'X-Secret':'private'}
        if fault=='body':r.arguments['secret']='private'
        if fault=='tool':r.tool='lookup_tax'
        if fault=='correlation':r.correlation_id=uuid4()
        if fault=='scenario':r.scenario='S-02'
        if fault=='token':auth='Bearer '+t.inference_token
        if fault=='revoked':broker.revoke(sid)
        with pytest.raises(EgressDenied):await tools.source_request(broker,r,auth)
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(sid,task(),delegate))
    assert not broker._grants


@pytest.mark.parametrize('status',[200,302])
def test_http_proxy_template_and_redirect(monkeypatch,status):
    routes=dict(tools.TOOL_ROUTES);routes['S-01']=replace(routes['S-01'],destination='https://source.example.invalid/rates')
    monkeypatch.setattr(tools,'TOOL_ROUTES',routes)
    original=httpx.AsyncClient;sent=[]
    def receive(req):
        sent.append(req)
        return httpx.Response(status,json={'simulated':True},headers={'Location':'https://other.example.invalid/'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
    broker=InferenceBroker()
    async def delegate(t):
        permit=tools.authorize_tool(broker,tool_request(t),'Bearer '+t.inference_token)
        r=source_request(t,permit)
        if status==302:
            with pytest.raises(EgressDenied):await tools.source_request(broker,r,'Bearer '+permit.source_token)
        else:assert await tools.source_request(broker,r,'Bearer '+permit.source_token)=={'simulated':True}
        with pytest.raises(EgressDenied):await tools.source_request(broker,r,'Bearer '+permit.source_token)
        assert len(sent)==1
        assert json.loads(sent[0].content)==t.view.model_dump(mode='json')
        assert 'authorization' not in sent[0].headers
        assert permit.source_token not in sent[0].content.decode()
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(uuid4(),task(),delegate))


@pytest.mark.parametrize('payload',[{'arguments':'opaque'},{'method':'PUT'},{'prompt':'secret'}])
def test_source_api_invalid_payload_sanitized(payload):
    from gateway.app import create_app
    r=source_request(task(),SimpleNamespace(destination='fixture://simulated-rates-v1')).model_dump(mode='json')
    r.update(payload)
    with TestClient(create_app()) as c:response=c.post('/internal/sources',json=r)
    assert response.status_code==422 and 'secret' not in response.text


def test_unregistered_mcp_connector_fails_closed(monkeypatch):
    from services.source_client import fetch_source
    for name in ('TESI_SOURCE_TOKEN','TESI_CORRELATION_ID','TESI_SCENARIO','TESI_SOURCE_DESTINATION','TESI_SOURCE_GATEWAY'):
        monkeypatch.delenv(name,raising=False)
    assert fetch_source('lookup_rates',{})=={'status':'blocked','error_code':'not_authorized'}


@pytest.mark.parametrize('deny_market',[False,True])
def test_whole_stack_real_a2a_mcp_gateway(monkeypatch,local_gateway,deny_market):
    from gateway.app import create_app
    import gateway.a2a_egress as a2a
    import gateway.market_client as market_client
    import gateway.tax_client as tax_client
    import services.market_agent as markets
    import services.tax_agent as tax
    import services.tool_client as tool_client
    import services.inference_client as inference_client
    original=httpx.AsyncClient;sent=[]
    real_ollama=os.environ.get('TESI_S01_REAL_OLLAMA')=='1'
    if deny_market:
        catalog=dict(tools.TOOL_ROUTES)
        catalog['S-01']=replace(catalog['S-01'],module='services.forbidden_source_mcp')
        monkeypatch.setattr(tools,'TOOL_ROUTES',catalog)
    class OllamaOnlyMock(httpx.AsyncBaseTransport):
        def __init__(self):self.real=httpx.AsyncHTTPTransport(trust_env=False)
        async def handle_async_request(self,req):
            if str(req.url)==OLLAMA_ENDPOINT:
                sent.append(json.loads(req.content))
                if real_ollama:return await self.real.handle_async_request(req)
                return httpx.Response(200,json={'message':{'content':'Sintesi simulata'},'prompt_eval_count':10,'eval_count':3,'load_duration':0})
            assert req.url.host=='127.0.0.1'
            return await self.real.handle_async_request(req)
        async def aclose(self):await self.real.aclose()
    def client(**kwargs):
        if 'transport' not in kwargs:kwargs['transport']=OllamaOnlyMock()
        return original(**kwargs)
    monkeypatch.setattr(httpx,'AsyncClient',client)
    with local_gateway(markets.app) as m,local_gateway(tax.app) as t,local_gateway(create_app()) as base:
        routes=dict(a2a.ROUTES);routes['S-01']=replace(routes['S-01'],endpoint=m+'/');routes['S-02']=replace(routes['S-02'],endpoint=t+'/')
        monkeypatch.setattr(a2a,'ROUTES',routes)
        for module,endpoint in [(market_client,m),(tax_client,t)]:
            monkeypatch.setattr(module,'ROUTES',routes);monkeypatch.setattr(module,'ENDPOINT',endpoint+'/')
        monkeypatch.setattr(markets.card,'url',m+'/');monkeypatch.setattr(tax.card,'url',t+'/')
        monkeypatch.setattr(tool_client,'GATEWAY_BASE',base)
        monkeypatch.setattr(inference_client,'GATEWAY_ENDPOINT',base+'/internal/inference')
        with httpx.Client(base_url=base,trust_env=False,timeout=135) as c:
            for case,expected in [('C001','partial' if deny_market else 'completed'),('C006','partial')]:
                files=[('files',(kind+'.pdf',(Path('dataset/Documents')/f'{case}_{kind}.pdf').read_bytes())) for kind in ['mutuo','interessi']]
                sid=c.post('/sessions/pdf',files=files,data={'scenarios':['S-01','S-02']}).json()['session_id']
                response=c.post(f'/sessions/{sid}/analysis');assert response.status_code==200,response.text
                body=response.json();assert body['status']==expected,body
                for scenario,activity in body['activities'].items():
                    if case=='C006' and scenario=='S-01':
                        assert activity['status']=='blocked' and activity['error_code']=='input_not_ready'
                        continue
                    if deny_market and scenario=='S-01':
                        assert activity['status']=='blocked' and activity['error_code']=='not_authorized',activity
                        assert activity['result']['measurements']['gateway_tool_authorized']==1
                        assert activity['result']['measurements']['gateway_source_authorized']==0
                        assert activity['result']['measurements']['gateway_inference_completed']==0
                        continue
                    assert activity['status']=='completed',activity
                    counts=activity['result']['measurements']
                    for key in ['gateway_tool_authorized','gateway_source_authorized','gateway_source_completed','gateway_inference_completed']:
                        assert counts[key]==1,(key,counts)
                assert 'source_token' not in response.text and 'inference_token' not in response.text
                assert c.delete(f'/sessions/{sid}').status_code==404
                evidence_path=os.environ.get('TESI_S01_EVIDENCE')
                if evidence_path:
                    row={'case':case,'real_ollama':real_ollama,'malicious_connector':deny_market,
                         'status':body['status'],'cleanup_verified':True,'passed':True,
                         'activities':{s:{'status':a['status'],'error_code':a.get('error_code'),
                             'phases':a['phases'],'measurements':a.get('result',{}).get('measurements',{})} for s,a in body['activities'].items()}}
                    with Path(evidence_path).open('a') as out:out.write(json.dumps(row)+'\n')
    assert len(sent)==(2 if deny_market else 3)
    assert not markets.task_store.tasks and not tax.task_store.tasks
