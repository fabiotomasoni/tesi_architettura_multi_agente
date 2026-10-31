"""Autenticazione e ponte in processo; le prove di rete reali sono separate."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from gateway import runtime
from gateway.app import create_app
from gateway.identity import AgentIdentityApp,HEADER,callback_headers
from gateway.ollama_bridge import OllamaBridge


@pytest.fixture
def isolated(monkeypatch,tmp_path):
    keys={k:hex(i)[2:]*64 for i,k in enumerate(('gateway_to_markets','gateway_to_tax','markets_to_gateway','tax_to_gateway','bridge'),1)}
    path=tmp_path/'identity.json'
    path.write_text(json.dumps({'role':'gateway','keys':keys}))
    monkeypatch.setattr(runtime,'ISOLATED',True)
    monkeypatch.setattr(runtime,'MODE','isolated')
    monkeypatch.setenv('TESI_IDENTITY_FILE',str(path))
    return keys,path


@pytest.mark.parametrize('path',['/internal/inference','/internal/tools/authorize','/internal/sources','/_bridge/poll'])
@pytest.mark.parametrize('kind',['absent','wrong','duplicate'])
def test_missing_wrong_duplicate_identity_denied(isolated,path,kind):
    keys,_=isolated
    headers=[] if kind=='absent' else [(HEADER,'0'*64)] if kind=='wrong' else [(HEADER,keys['markets_to_gateway'])]*2
    with TestClient(create_app()) as client:
        r=client.request('GET' if path.endswith('poll') else 'POST',path,headers=headers,json={})
        assert r.status_code==403
        assert keys['markets_to_gateway'] not in r.text


def test_valid_identity_does_not_replace_task_capability(isolated):
    keys,_=isolated
    with TestClient(create_app()) as client:
        r=client.post('/internal/tools/authorize',headers={HEADER:keys['markets_to_gateway']},json={'correlation_id':str(uuid4()),'scenario':'S-01','tool':'lookup_rates','arguments':{}})
        assert r.status_code==403


def test_wrong_role_does_not_reach_broker(isolated):
    keys,_=isolated
    with TestClient(create_app()) as client:
        r=client.post('/internal/inference',headers={HEADER:keys['markets_to_gateway']},json={'correlation_id':str(uuid4()),'scenario':'S-02','evidence':{}})
        assert r.status_code==403


def test_peer_cannot_reach_public_api_or_spoof_other_role(isolated):
    keys,_=isolated
    with TestClient(create_app(),client=('172.30.241.3',1234)) as client:
        assert client.get('/health').status_code==403
        assert client.post('/sessions',json={}).status_code==403
        assert client.get('/_bridge/poll',headers={HEADER:keys['bridge']}).status_code==403
        assert client.post('/internal/inference',headers={HEADER:keys['tax_to_gateway']},json={}).status_code==403


def test_identity_does_not_use_forwarded_headers(isolated):
    keys,_=isolated
    with TestClient(create_app(),client=('172.30.241.3',1234)) as client:
        r=client.get('/health',headers={'X-Forwarded-For':'127.0.0.1','Forwarded':'for=127.0.0.1'})
        assert r.status_code==403


def test_agent_card_requires_correct_directional_key(isolated):
    keys,path=isolated
    path.write_text(json.dumps({'role':'markets','keys':{k:v for k,v in keys.items() if k.endswith('markets') or k.startswith('markets')}}))
    from fastapi import FastAPI
    inner=FastAPI()
    @inner.get('/.well-known/agent-card.json')
    def card():return {'ok':True}
    with TestClient(AgentIdentityApp(inner,'S-01')) as client:
        for key in (None,keys['markets_to_gateway'],keys['gateway_to_tax']):
            assert client.get('/.well-known/agent-card.json',headers={HEADER:key} if key else {}).status_code==403
        assert client.get('/.well-known/agent-card.json',headers={HEADER:keys['gateway_to_markets']}).status_code==200


def test_bridge_single_delivery_and_stale_reply():
    async def run():
        bridge=OllamaBridge()
        pending=asyncio.create_task(bridge.infer({'test':'fixture'},1))
        job=await bridge.poll()
        assert job['payload']=={'test':'fixture'}
        assert bridge.complete(job['job_id'],body={'ok':True})
        assert not bridge.complete(job['job_id'],body={'ok':False})
        assert await pending=={'body':{'ok':True},'ollama_ms':None}
        assert not bridge.pending
        assert not bridge.complete(job['job_id'],body={})
    asyncio.run(run())


@pytest.mark.parametrize('mode',['timeout','cancel','close'])
def test_bridge_finalization(mode):
    async def run():
        bridge=OllamaBridge()
        pending=asyncio.create_task(bridge.infer({},0.02 if mode=='timeout' else 10))
        job=await bridge.poll()
        if mode=='cancel':pending.cancel()
        if mode=='close':bridge.close()
        with pytest.raises((TimeoutError,asyncio.CancelledError,RuntimeError)):await pending
        assert not bridge.pending and not bridge.complete(job['job_id'],body={})
    asyncio.run(run())


def test_bridge_rejects_arbitrary_prompt_and_options():
    from scripts.run_ollama_bridge import validate_payload
    from gateway.inference import MODELS,PROMPTS
    from gateway.market_evidence import expected_evidence
    from gateway.agent_contracts import MarketView
    evidence=expected_evidence(MarketView(mortgage_type='other',rate_type='fixed',remaining_years_band={'lower_exclusive':0,'upper_inclusive':5})).model_dump(mode='json')
    payload={'model':MODELS['S-01'],'stream':False,'keep_alive':0,'options':{'num_ctx':4096,'num_predict':200,'temperature':0},'messages':[{'role':'system','content':PROMPTS['S-01']},{'role':'user','content':json.dumps(evidence)}]}
    assert validate_payload(payload)==payload
    for field,value in [('model','unconfigured'),('options',{}),('url','http://example.invalid/')]:
        with pytest.raises(ValueError):validate_payload({**payload,field:value})
    payload['messages'][1]['content']='arbitrary text'
    with pytest.raises(ValueError):validate_payload(payload)


def test_expired_jobs_without_worker_do_not_poison_next_request():
    async def run():
        bridge=OllamaBridge()
        for _ in range(3):
            with pytest.raises(TimeoutError):await bridge.infer({},0.001)
        assert not bridge.pending and bridge.queue.empty()
        active=asyncio.create_task(bridge.infer({},1))
        job=await bridge.poll();bridge.complete(job['job_id'],body={'ok':True})
        assert await active=={'body':{'ok':True},'ollama_ms':None}
    asyncio.run(run())


def test_bridge_rejects_third_concurrent_job():
    async def run():
        bridge=OllamaBridge()
        jobs=[asyncio.create_task(bridge.infer({},1)) for _ in range(2)]
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError):await bridge.infer({},1)
        for pending in jobs:pending.cancel()
        await asyncio.gather(*jobs,return_exceptions=True)
        assert not bridge.pending and bridge.queue.empty()
    asyncio.run(run())


def test_bridge_api_claim_completion_replay_and_size_limit(isolated,monkeypatch):
    import importlib,httpx
    from gateway.inference import InferenceBroker
    module=importlib.import_module('gateway.app');broker=InferenceBroker()
    monkeypatch.setattr(module,'InferenceBroker',lambda:broker)
    app=create_app();keys,_=isolated
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as client:
            pending=asyncio.create_task(broker.bridge.infer({'simulated':True},2))
            response=await client.get('/_bridge/poll',headers={HEADER:keys['bridge']})
            assert response.status_code==200
            job=response.json();url='/_bridge/result/'+job['job_id'];headers={HEADER:keys['bridge']}
            bad=await client.post(url,headers=headers,json={'body':{},'error':None,'extra':'private'})
            assert bad.status_code==422 and 'private' not in bad.text
            large=await client.post(url,headers=headers,content=b'x'*65537)
            assert large.status_code==413
            response=await client.post(url,headers=headers,json={'body':{'ok':True},'error':None,'ollama_ms':1})
            assert response.status_code==200 and await pending=={'body':{'ok':True},'ollama_ms':1}
            assert (await client.post(url,headers=headers,json={'body':{},'error':None,'ollama_ms':1})).status_code==409
            assert not broker.bridge.pending
    asyncio.run(run())


def test_source_role_and_inference_with_bridge_and_capabilities(isolated,monkeypatch):
    import importlib,httpx
    from gateway.inference import InferenceBroker
    from gateway.agent_contracts import TaxTask
    module=importlib.import_module('gateway.app');broker=InferenceBroker()
    monkeypatch.setattr(module,'InferenceBroker',lambda:broker)
    app=create_app();keys,_=isolated
    task=TaxTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=20),view={'tax_year':2025,'purpose':'renovation'})
    async def remote(t):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as client:
            data={'correlation_id':str(t.correlation_id),'scenario':t.scenario,'tool':'lookup_tax','arguments':t.view.model_dump(mode='json')}
            header={HEADER:keys['tax_to_gateway'],'Authorization':'Bearer '+t.inference_token}
            assert (await client.post('/internal/tools/authorize',headers={**header,HEADER:keys['markets_to_gateway']},json=data)).status_code==403
            response=await client.post('/internal/tools/authorize',headers=header,json=data)
            assert response.status_code==200
            permit=response.json()
            response=await client.post('/internal/sources',headers={HEADER:keys['tax_to_gateway'],'Authorization':'Bearer '+permit['source_token']},json={**data,'destination':permit['destination'],'headers':{}})
            assert response.status_code==200
            body={'correlation_id':str(t.correlation_id),'scenario':t.scenario,'evidence':response.json()}
            request=asyncio.create_task(client.post('/internal/inference',headers=header,json=body))
            job=(await client.get('/_bridge/poll',headers={HEADER:keys['bridge']})).json()
            assert t.inference_token not in json.dumps(job) and keys['tax_to_gateway'] not in json.dumps(job)
            response=await client.post('/_bridge/result/'+job['job_id'],headers={HEADER:keys['bridge']},json={'body':{'message':{'content':'Simulazione'},'prompt_eval_count':1,'eval_count':1,'load_duration':0},'error':None,'ollama_ms':1})
            assert response.status_code==200 and (await request).status_code==200
            assert (await client.post('/internal/inference',headers=header,json=body)).status_code==403
        return SimpleNamespace(measurements={})
    result=asyncio.run(broker.delegate(uuid4(),task,remote))
    assert result.measurements['gateway_inference_completed']==1
    assert result.measurements['workload_identity_enforced']==1
    assert not broker._grants and not broker.bridge.pending


@pytest.mark.parametrize('change,expected',[
 ('short_name',True),('canonical_name',True),('extra_capability',False),
 ('privileged',False),('writable_root',False),('socket_mount',False)])
def test_guard_inspection_normalizes_capability_names_without_broadening(change,expected):
    from scripts.check_isolation import guard_policy
    info={'HostConfig':{'Privileged':False,'ReadonlyRootfs':True,'CapDrop':['ALL'],
                       'CapAdd':['CAP_NET_ADMIN'],'SecurityOpt':['no-new-privileges:true']},'Mounts':[]}
    if change=='short_name':info['HostConfig']['CapAdd']=['NET_ADMIN']
    if change=='extra_capability':info['HostConfig']['CapAdd'].append('CAP_NET_RAW')
    if change=='privileged':info['HostConfig']['Privileged']=True
    if change=='writable_root':info['HostConfig']['ReadonlyRootfs']=False
    if change=='socket_mount':info['Mounts']=[{'Type':'bind','Destination':'/var/run/docker.sock'}]
    assert guard_policy(info) is expected
