"""Inferenza autorizzata e revoca, senza Ollama o rete esterna."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway.a2a_egress import EgressDenied
from gateway.agent_contracts import MarketTask, TaxTask
from gateway.inference import InferenceBroker, InferenceRequest, MODELS, OLLAMA_ENDPOINT
from gateway.market_evidence import expected_evidence as market_evidence
from gateway.tax_evidence import expected_evidence as tax_evidence


def task(fiscal=False):
    data={'correlation_id':uuid4(),'deadline':datetime.now(timezone.utc)+timedelta(seconds=60)}
    if fiscal:return TaxTask(**data,view={'tax_year':2025,'purpose':'renovation'})
    return MarketTask(**data,view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})


def request(t):
    evidence=(tax_evidence if t.scenario=='S-02' else market_evidence)(t.view)
    return InferenceRequest(correlation_id=t.correlation_id,scenario=t.scenario,evidence=evidence.model_dump(mode='json'))


def mock_ollama(monkeypatch, *, status=200):
    sent=[]; original=httpx.AsyncClient
    def receive(req):
        sent.append(req)
        return httpx.Response(status,json={'message':{'content':'Sintesi simulata'},'prompt_eval_count':12,'eval_count':4,'load_duration':1000000},headers={'Location':'http://example.invalid/'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
    return sent


@pytest.mark.parametrize('fiscal',[False,True])
def test_nominal_payload_and_single_use(monkeypatch,fiscal):
    sent=mock_ollama(monkeypatch); broker=InferenceBroker(); t=task(fiscal); sid=uuid4(); token=[]
    async def delegate(authorized):
        token.append(authorized.inference_token)
        r=request(authorized); header='Bearer '+authorized.inference_token
        result=await broker.infer(r,header)
        assert result.model==MODELS[t.scenario] and result.output_tokens==4
        with pytest.raises(EgressDenied):await broker.infer(r,header)
        from types import SimpleNamespace
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(sid,t,delegate))
    assert not broker._grants and len(sent)==1
    wire=sent[0]; payload=json.loads(wire.content)
    assert str(wire.url)==OLLAMA_ENDPOINT
    assert payload['model']==MODELS[t.scenario]
    assert json.loads(payload['messages'][1]['content'])==request(t).evidence
    assert payload['options']=={'num_ctx':4096,'num_predict':200,'temperature':0}
    assert payload['keep_alive']==0 and payload['stream'] is False
    if fiscal:assert payload['think'] is False
    assert token[0] not in wire.content.decode() and token[0] not in str(wire.headers)
    assert str(t.correlation_id) not in wire.content.decode()


@pytest.mark.parametrize('fault',['absent','wrong_token','correlation','scenario','expired','altered','missing_source','extra_evidence','revoked'])
def test_denied_before_ollama(monkeypatch,fault):
    sent=mock_ollama(monkeypatch); broker=InferenceBroker(); t=task(); sid=uuid4()
    async def delegate(authorized):
        r=request(authorized); header='Bearer '+authorized.inference_token
        if fault=='absent':header=None
        if fault=='wrong_token':header='Bearer '+'0'*64
        if fault=='correlation':r=r.model_copy(update={'correlation_id':uuid4()})
        if fault=='scenario':r=r.model_copy(update={'scenario':'S-02'})
        if fault=='expired':broker._grants[authorized.inference_token].task.deadline=datetime.now(timezone.utc)-timedelta(seconds=1)
        if fault=='altered':r.evidence['annual_rate_percent']='9.99'
        if fault=='missing_source':del r.evidence['source_id']
        if fault=='extra_evidence':r.evidence['secret']='private value'
        if fault=='revoked':broker.revoke(sid)
        with pytest.raises(EgressDenied):await broker.infer(r,header)
        from types import SimpleNamespace
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(sid,t,delegate))
    assert not sent and not broker._grants


@pytest.mark.parametrize('mode',['exception','cancel'])
def test_delegate_revokes_on_every_exit(mode):
    broker=InferenceBroker()
    async def delegate(t):
        assert broker._grants
        if mode=='cancel':raise asyncio.CancelledError()
        raise RuntimeError('test')
    with pytest.raises(asyncio.CancelledError if mode=='cancel' else RuntimeError):
        asyncio.run(broker.delegate(uuid4(),task(),delegate))
    assert not broker._grants


def test_redirect_no_retry(monkeypatch):
    sent=mock_ollama(monkeypatch,status=302); broker=InferenceBroker()
    async def delegate(t):
        with pytest.raises(EgressDenied):await broker.infer(request(t),'Bearer '+t.inference_token)
        with pytest.raises(EgressDenied):await broker.infer(request(t),'Bearer '+t.inference_token)
        from types import SimpleNamespace
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(uuid4(),task(),delegate))
    assert len(sent)==1 and not broker._grants


@pytest.mark.parametrize('field',['model','prompt','url','options'])
def test_api_rejects_arbitrary_fields(field):
    from gateway.app import create_app
    payload=request(task()).model_dump(mode='json');payload[field]='secret'
    with TestClient(create_app()) as client:
        result=client.post('/internal/inference',json=payload)
    assert result.status_code==422 and 'secret' not in result.text


def test_api_rejects_unregistered_task():
    from gateway.app import create_app
    with TestClient(create_app()) as client:
        result=client.post('/internal/inference',json=request(task()).model_dump(mode='json'))
    assert result.status_code==403


@pytest.mark.parametrize('fail_market',[False,True])
def test_multi_real_mcp_and_inference_roundtrip(monkeypatch,fail_market,local_gateway):
    from gateway.app import create_app
    import gateway.market_client as market
    import gateway.tax_client as tax
    from services.market_work import perform as market_work
    from services.tax_work import perform as tax_work
    from gateway.agent_contracts import MarketResult
    app=create_app(); sent=[]; original=httpx.AsyncClient
    class Router(httpx.AsyncBaseTransport):
        async def handle_async_request(self,req):
            if str(req.url)==OLLAMA_ENDPOINT:
                payload=json.loads(req.content);sent.append(payload)
                if fail_market and payload['model']==MODELS['S-01']:
                    raise httpx.ReadTimeout('private failure')
                return httpx.Response(200,json={'message':{'content':'Sintesi simulata'},'prompt_eval_count':12,'eval_count':4,'load_duration':0})
            assert req.url.path in {'/internal/inference','/internal/tools/authorize'}
            return await httpx.ASGITransport(app=app).handle_async_request(req)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=Router(),**kw))
    async def markets(t):
        try:return await market_work(t)
        except TimeoutError:
            return MarketResult(correlation_id=t.correlation_id,status='failed',error_code='timeout',summary='Timeout',limits=[],model=MODELS['S-01'])
    monkeypatch.setattr(market,'delegate',markets)
    monkeypatch.setattr(tax,'delegate',tax_work)
    import services.tool_client as tools
    with local_gateway(app) as base:
        monkeypatch.setattr(tools,'GATEWAY_BASE',base)
        with TestClient(app) as client:
            data=json.loads(Path('examples/session_complete.json').read_text()); data['scenarios']=['S-01','S-02']
            sid=client.post('/sessions',json=data).json()['session_id']
            result=client.post(f'/sessions/{sid}/analysis')
            assert result.status_code==200,result.text
            body=result.json()
            assert body['status']==('partial' if fail_market else 'completed'),body
            assert body['activities']['S-02']['status']=='completed'
            assert body['activities']['S-02']['result']['measurements']['inference_via_gateway']==1
            assert body['activities']['S-02']['result']['measurements']['gateway_inference_completed']==1
            assert body['activities']['S-01']['result']['measurements']['gateway_inference_authorized']==1
            assert body['activities']['S-01']['result']['measurements']['gateway_inference_completed']==(0 if fail_market else 1)
            if fail_market:assert body['activities']['S-01']['error_code']=='timeout'
            assert body['session_closed'] and client.delete(f'/sessions/{sid}').status_code==404
            assert 'private failure' not in result.text and 'inference_token' not in result.text
    assert len(sent)==2


def test_revoked_inflight_result_is_not_delivered(monkeypatch):
    broker=InferenceBroker(); sid=uuid4(); original=httpx.AsyncClient
    async def run():
        entered=asyncio.Event(); release=asyncio.Event()
        async def receive(req):
            entered.set(); await release.wait()
            return httpx.Response(200,json={'message':{'content':'late'},'prompt_eval_count':1,'eval_count':1,'load_duration':0})
        monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
        async def delegate(t):
            running=asyncio.create_task(broker.infer(request(t),'Bearer '+t.inference_token))
            await entered.wait(); broker.revoke(sid); release.set()
            with pytest.raises(EgressDenied):await running
            from types import SimpleNamespace
            return SimpleNamespace(measurements={})
        result=await broker.delegate(sid,task(),delegate)
        assert result.measurements['gateway_inference_completed']==0
    asyncio.run(run())
    assert not broker._grants


@pytest.mark.parametrize('fiscal',[False,True])
def test_agent_returns_blocked_and_cleans_on_inference_denial(monkeypatch,fiscal):
    if fiscal:import services.tax_agent as agent
    else:import services.market_agent as agent
    async def denied(t):raise EgressDenied('test')
    monkeypatch.setattr(agent,'perform',denied)
    t=task(fiscal)
    with TestClient(agent.app) as client:
        response=client.post('/',json={'jsonrpc':'2.0','id':'denied','method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':t.model_dump_json()}]}}})
    data=response.json()['result'];parts=data.get('parts',[])+[p for a in data.get('artifacts',[]) for p in a['parts']]
    result=json.loads(next(p['text'] for p in parts if p['kind']=='text'))
    assert result['status']=='blocked' and result['error_code']=='not_authorized' and result['evidence'] is None
    assert not agent.task_store.tasks
    assert not asyncio.run(agent.session_service.list_sessions(app_name='tax_demo' if fiscal else 'markets_demo')).sessions
