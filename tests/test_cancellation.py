"""Annullamento su HTTP, grafo, capability e ponte; fixture dichiarate, nessun LLM."""
import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import threading
from uuid import uuid4

import httpx
import pytest

from gateway import runtime
from gateway.a2a_egress import EgressDenied
from gateway.agent_contracts import MarketResult, MarketTask, TaxResult
from gateway.inference import InferenceBroker, InferenceRequest, MODELS
from gateway.ollama_bridge import OllamaBridge
from gateway.tool_egress import ToolRequest, SourceRequest, authorize_tool, source_request

MODEL_BODY = {'message':{'content':'Risposta controllata, non prodotta da Ollama.'},
              'prompt_eval_count':1, 'eval_count':1, 'load_duration':0}


@pytest.fixture
def setup(monkeypatch, tmp_path):
    module = importlib.import_module('gateway.app')
    keys = {name:format(i, '064x') for i, name in enumerate(
        ['gateway_to_markets','gateway_to_tax','markets_to_gateway','tax_to_gateway','bridge'],1)}
    path = tmp_path/'identity.json'
    path.write_text(json.dumps({'role':'gateway','keys':keys}))
    monkeypatch.setenv('TESI_IDENTITY_FILE', str(path))
    monkeypatch.setattr(runtime, 'ISOLATED', True)
    monkeypatch.setattr(runtime, 'MODE', 'isolated')
    broker = InferenceBroker()
    monkeypatch.setattr(module, 'InferenceBroker', lambda:broker)
    app = module.create_app()
    seen = []
    stopped = set()
    async def remote(task):
        permit_request = ToolRequest(correlation_id=task.correlation_id, scenario=task.scenario,
            tool='lookup_rates' if task.scenario=='S-01' else 'lookup_tax', arguments=task.view.model_dump(mode='json'))
        permit = authorize_tool(broker, permit_request, 'Bearer '+task.inference_token)
        request = SourceRequest(**permit_request.model_dump(), destination=permit.destination, headers={})
        evidence = await source_request(broker, request, 'Bearer '+permit.source_token)
        inference = InferenceRequest(correlation_id=task.correlation_id, scenario=task.scenario, evidence=evidence)
        seen.append((task, request, permit, inference))
        try:
            reply = await broker.infer(inference, 'Bearer '+task.inference_token)
            result_type = MarketResult if task.scenario=='S-01' else TaxResult
            return result_type(correlation_id=task.correlation_id, status='completed', evidence=evidence,
                summary=reply.summary, limits=[], model=MODELS[task.scenario],measurements={'agent_boot_id':'controlled-test-'+task.scenario})
        finally:
            stopped.add(task.correlation_id)
    monkeypatch.setattr('gateway.market_client.delegate', remote)
    monkeypatch.setattr('gateway.tax_client.delegate', remote)
    return app, broker, keys, seen, stopped


def payload(scenarios):
    data = json.loads(Path('examples/session_complete.json').read_text())
    data['scenarios'] = scenarios
    return data


@pytest.mark.parametrize('endpoint', ['analysis','workflow','markets'])
def test_delete_revokes_every_boundary_blocks_late_result_and_allows_recovery(setup, endpoint):
    app, broker, keys, seen, stopped = setup
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
            scenarios = ['S-01','S-02'] if endpoint=='analysis' else ['S-01']
            sid = (await client.post('/sessions', json=payload(scenarios))).json()['session_id']
            running = asyncio.create_task(client.post(f'/sessions/{sid}/{endpoint}'))
            jobs = [await asyncio.wait_for(broker.bridge.poll(), 3) for _ in scenarios]
            duplicate = await client.post(f'/sessions/{sid}/analysis')
            assert duplicate.status_code==409 and duplicate.json()['detail']['error_code']=='analysis_already_running'
            assert (await client.delete('/sessions/'+sid)).status_code==204
            response = await asyncio.wait_for(running, 3)
            assert response.status_code==409 and response.json()['error_code']=='analysis_cancelled'
            assert 'report' not in response.json()
            assert len(stopped)==len(scenarios)
            assert not broker._grants and not broker._privacy and not broker._lab_profiles
            assert not broker.bridge.pending and broker.bridge.queue.empty()
            for job in jobs:
                headers = {'x-tesi-service-key':keys['bridge']}
                assert (await client.get('/_bridge/status/'+job['job_id'],headers=headers)).status_code==409
                assert (await client.post('/_bridge/result/'+job['job_id'],headers=headers,
                    json={'body':MODEL_BODY,'error':None,'ollama_ms':1})).status_code==409
            for task, request, permit, inference in seen:
                headers = {'x-tesi-service-key':keys['markets_to_gateway' if task.scenario=='S-01' else 'tax_to_gateway'],
                           'authorization':'Bearer '+task.inference_token}
                assert (await client.post('/internal/inference',headers=headers,json=inference.model_dump(mode='json'))).status_code==403
                assert (await client.post('/internal/tools/authorize',headers=headers,
                    json=request.model_dump(mode='json',exclude={'destination','method','headers'}))).status_code==403
                headers['authorization'] = 'Bearer '+permit.source_token
                assert (await client.post('/internal/sources',headers=headers,json=request.model_dump(mode='json'))).status_code==403
            assert (await client.delete('/sessions/'+sid)).status_code==404
            second = (await client.post('/sessions',json=payload(['S-01','S-02']))).json()['session_id']
            recovery = asyncio.create_task(client.post(f'/sessions/{second}/analysis'))
            for _ in range(2):
                job = await asyncio.wait_for(broker.bridge.poll(), 3)
                broker.bridge.complete(job['job_id'],body=MODEL_BODY,ollama_ms=1)
            response = await asyncio.wait_for(recovery, 3)
            assert response.status_code==200 and response.json()['status']=='completed'
            assert (await client.delete('/sessions/'+second)).status_code==404
    asyncio.run(exercise())


def test_expiry_stops_active_graph_without_waiting_for_new_request(setup, monkeypatch):
    app, broker, _, _, _ = setup
    module = importlib.import_module('gateway.app')
    clock = [0.0]
    monkeypatch.setattr(module, 'monotonic', lambda:clock[0])
    monkeypatch.setattr(module, 'SESSION_TTL_SECONDS', 1)
    monkeypatch.setattr(module, 'SESSION_SWEEP_SECONDS', .01)
    async def exercise():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as client:
                sid = (await client.post('/sessions',json=payload(['S-01']))).json()['session_id']
                running = asyncio.create_task(client.post(f'/sessions/{sid}/analysis'))
                await asyncio.wait_for(broker.bridge.poll(),3)
                clock[0] = 2.0
                response = await asyncio.wait_for(running,3)
                assert response.json()['reason']=='session_expired'
                assert not broker._grants and not broker.bridge.pending and not broker._privacy
    asyncio.run(exercise())


def test_real_http_disconnect_cleans_gateway_and_next_session_works(monkeypatch, local_gateway):
    module = importlib.import_module('gateway.app')
    broker = InferenceBroker()
    monkeypatch.setattr(module, 'InferenceBroker', lambda:broker)
    entered = threading.Event(); stopped = threading.Event(); calls = []
    async def remote(task):
        calls.append(task.correlation_id)
        if len(calls)==1:
            entered.set()
            try:await asyncio.Event().wait()
            finally:stopped.set()
        from gateway.market_evidence import expected_evidence
        return MarketResult(correlation_id=task.correlation_id,status='completed',evidence=expected_evidence(task.view),summary='Fixture',limits=[],model='test')
    monkeypatch.setattr('gateway.market_client.delegate',remote)
    with local_gateway(module.create_app()) as base:
        async def exercise():
            async with httpx.AsyncClient(base_url=base,trust_env=False,timeout=5) as client:
                sid = (await client.post('/sessions',json=payload(['S-01']))).json()['session_id']
                running = asyncio.create_task(client.post(f'/sessions/{sid}/analysis'))
                assert await asyncio.to_thread(entered.wait,3)
                running.cancel()
                with suppress(asyncio.CancelledError):await running
                assert await asyncio.to_thread(stopped.wait,3)
                assert (await client.delete('/sessions/'+sid)).status_code==404
                assert not broker._privacy and not broker._grants
                sid = (await client.post('/sessions',json=payload(['S-01']))).json()['session_id']
                result = await client.post(f'/sessions/{sid}/analysis')
                assert result.status_code==200 and result.json()['status']=='completed'
        asyncio.run(exercise())


def test_bridge_revocation_only_removes_the_owning_grant():
    async def exercise():
        bridge = OllamaBridge()
        first = asyncio.create_task(bridge.infer({'fixture':1},3,owner='first'))
        second = asyncio.create_task(bridge.infer({'fixture':2},3,owner='second'))
        jobs = [await bridge.poll(),await bridge.poll()]
        bridge.revoke('first')
        with pytest.raises(EgressDenied):await first
        assert len(bridge.pending)==1 and bridge.is_active(jobs[1]['job_id'])
        assert not bridge.complete(jobs[0]['job_id'],body={})
        bridge.complete(jobs[1]['job_id'],body={'ok':True})
        assert (await second)['body']=={'ok':True}
        assert not bridge.pending and bridge.queue.empty()
    asyncio.run(exercise())


def test_manual_checker_cancels_then_recovers_without_confusing_fixture_with_ollama(setup):
    from scripts.check_cancellation import check
    app,broker,keys,seen,_=setup
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as client:
            result=await check(client,keys['bridge'])
            assert result['passed'],result
            assert 'not_actual_ollama_or_final_campaign' in result['scope']
            assert len(seen)==6 and not broker._privacy and not broker._grants and not broker.bridge.pending
    asyncio.run(exercise())


def test_closed_session_cannot_authorize_a_new_delegation():
    async def exercise():
        broker=InferenceBroker();broker.require_session=True
        called=[]
        async def remote(task):called.append(True)
        task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=10),
            view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
        with pytest.raises(EgressDenied):await broker.delegate(uuid4(),task,remote)
        assert not called and not broker._grants
    asyncio.run(exercise())


def test_direct_delivery_write_error_still_removes_profile_grants_jobs_and_recovers(setup):
    app,broker,keys,_,_=setup
    from scripts.check_finalization import ControlledDemo
    observed=[]
    async def broken_send_app(scope,receive,send):
        async def broken_send(message):
            if scope['path'].endswith('/analysis') and message['type']=='http.response.body' and message.get('body'):
                result=json.loads(message['body'])
                observed.append({'completed':result.get('status')=='completed' and result.get('report') is not None,
                                 'trace_id':result.get('trace_id')})
                raise BrokenPipeError('Controlled ASGI write failure')
            await send(message)
        await app(scope,receive,broken_send)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as client:
            lab=ControlledDemo(client,keys['bridge'])
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(broken_send_app),base_url='http://test') as broken:
                    sid=await lab.upload();request=lab.start(sid,broken)
                    jobs=await lab.complete_two()
                    with pytest.raises(BrokenPipeError):await request
                assert len(observed)==1 and observed[0]['completed']
                trace=(await client.get('/traces/'+observed[0]['trace_id'])).json()
                assert trace['profile_closed'] and trace['summary']['trace_complete']
                assert any(s['phase']=='asgi_delivery' and s['outcome']=='failed' and s['metrics']['asgi_body_complete']==0 for s in trace['spans'])
                assert not broker._privacy and not broker._lab_profiles and not broker._grants
                assert not broker.bridge.pending and broker.bridge.queue.empty()
                checks={};await lab.closed(sid,checks,'old');await lab.stale(jobs,checks,'old')
                await lab.nominal(checks,'recovery')
                assert all(checks.values()),checks
            finally:await lab.cleanup()
    asyncio.run(exercise())


def test_delivery_checker_actually_truncates_downstream_after_complete_upstream(setup):
    from scripts.check_finalization import ControlledDemo,check_delivery
    app,broker,keys,seen,_=setup
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as client:
            result=await check_delivery(ControlledDemo(client,keys['bridge']))
            assert result['passed'],result
            assert result['checks']['report_generated_before_delivery_fault']
            assert result['checks']['application_body_bytes_delivered_zero']
            assert result['checks']['client_delivery_failed']
            assert len(seen)==6
            assert not broker._privacy and not broker._grants and not broker.bridge.pending
    asyncio.run(exercise())


def test_gateway_boot_identifier_changes_only_with_application_start():
    from fastapi.testclient import TestClient
    from gateway.app import create_app
    with TestClient(create_app()) as first,TestClient(create_app()) as second:
        before=first.get('/health').json()['gateway_boot_id']
        assert before==first.get('/health').json()['gateway_boot_id']
        assert before!=second.get('/health').json()['gateway_boot_id']
        assert len(before)==32


def test_fresh_gateway_rejects_previously_valid_capabilities_and_bridge_results(setup,monkeypatch):
    app,old_broker,keys,seen,_=setup
    module=importlib.import_module('gateway.app')
    fresh_broker=InferenceBroker()
    monkeypatch.setattr(module,'InferenceBroker',lambda:fresh_broker)
    fresh=module.create_app()
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://old') as old:
            sid=(await old.post('/sessions',json=payload(['S-01','S-02']))).json()['session_id']
            pending=asyncio.create_task(old.post(f'/sessions/{sid}/analysis'))
            jobs=[await old_broker.bridge.poll(),await old_broker.bridge.poll()]
            try:
                # Le credenziali di servizio restano identiche, le capability no.
                async with httpx.AsyncClient(transport=httpx.ASGITransport(fresh),base_url='http://new') as new:
                    for task,source,permit,inference in seen:
                        role='markets_to_gateway' if task.scenario=='S-01' else 'tax_to_gateway'
                        headers={'x-tesi-service-key':keys[role],'authorization':'Bearer '+task.inference_token}
                        assert (await new.post('/internal/inference',headers=headers,json=inference.model_dump(mode='json'))).status_code==403
                        tool=source.model_dump(mode='json',exclude={'destination','method','headers'})
                        assert (await new.post('/internal/tools/authorize',headers=headers,json=tool)).status_code==403
                        headers['authorization']='Bearer '+permit.source_token
                        assert (await new.post('/internal/sources',headers=headers,json=source.model_dump(mode='json'))).status_code==403
                    for job in jobs:
                        headers={'x-tesi-service-key':keys['bridge']}
                        assert (await new.post('/_bridge/result/'+job['job_id'],headers=headers,
                            json={'body':MODEL_BODY,'error':None,'ollama_ms':1})).status_code==409
                    assert (await new.delete('/sessions/'+sid)).status_code==404
                assert not fresh_broker._grants and not fresh_broker._privacy and not fresh_broker._lab_profiles
                assert not fresh_broker.bridge.pending and fresh_broker.bridge.queue.empty()
            finally:
                await old.delete('/sessions/'+sid)
                await pending
    asyncio.run(exercise())


def test_host_bridge_cancels_local_request_when_gateway_revokes(monkeypatch):
    from scripts.run_ollama_bridge import execute_live_job
    async def exercise():
        entered=asyncio.Event(); stopped=asyncio.Event()
        async def work(*args):
            entered.set()
            try:await asyncio.Event().wait()
            finally:stopped.set()
        monkeypatch.setattr('scripts.run_ollama_bridge.execute_payload',work)
        checks=[]
        def response(request):
            checks.append(request)
            return httpx.Response(204 if len(checks)==1 else 409)
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as gateway:
            result=await asyncio.wait_for(execute_live_job({'job_id':'fixture','payload':{}},gateway,None),2)
            assert result is None and entered.is_set() and stopped.is_set()
    asyncio.run(exercise())


@pytest.mark.parametrize('fiscal',[False,True])
def test_a2a_disconnect_cancels_actual_mcp_process_cleans_adk_and_recovers(monkeypatch,local_gateway,fiscal):
    agent=importlib.import_module('services.tax_agent' if fiscal else 'services.market_agent')
    from mcp.client.stdio import stdio_client
    from mcp import ClientSession, StdioServerParameters
    import mcp.client.stdio as stdio
    import sys
    entered=threading.Event();stopped=threading.Event();processes=[];calls=[]
    original=stdio._create_platform_compatible_process
    async def process(*args,**kwargs):
        child=await original(*args,**kwargs);processes.append(child);return child
    monkeypatch.setattr(stdio,'_create_platform_compatible_process',process)
    async def perform(task):
        calls.append(task)
        if len(calls)==1:
            try:
                async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','services.slow_rates_mcp'])) as streams:
                    async with ClientSession(*streams) as client:
                        await client.initialize();entered.set()
                        await client.call_tool('lookup_rates',{'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
            finally:stopped.set()
        from gateway.market_evidence import expected_evidence as markets
        from gateway.tax_evidence import expected_evidence as tax
        return (TaxResult if fiscal else MarketResult)(correlation_id=task.correlation_id,status='completed',evidence=(tax if fiscal else markets)(task.view),summary='Fixture',limits=[],model='test')
    monkeypatch.setattr(agent,'perform',perform)
    def message():
        from gateway.agent_contracts import TaxTask
        task=(TaxTask if fiscal else MarketTask)(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=30),
            view={'tax_year':2025,'purpose':'renovation'} if fiscal else {'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
        return {'jsonrpc':'2.0','id':uuid4().hex,'method':'message/send','params':{'message':{'messageId':uuid4().hex,'role':'user','parts':[{'kind':'text','text':task.model_dump_json()}]}}}
    with local_gateway(agent.app) as base:
        async def exercise():
            async with httpx.AsyncClient(base_url=base,timeout=8,trust_env=False) as client:
                running=asyncio.create_task(client.post('/',json=message()))
                assert await asyncio.to_thread(entered.wait,5)
                running.cancel()
                with suppress(asyncio.CancelledError):await running
                assert await asyncio.to_thread(stopped.wait,5)
                reply=await client.post('/',json=message())
                assert reply.status_code==200 and 'error' not in reply.json()
                parts=reply.json()['result'].get('parts',[])
                for artifact in reply.json()['result'].get('artifacts',[]):
                    parts.extend(artifact.get('parts',[]))
                result=json.loads(next(p['text'] for p in parts if p['kind']=='text'))
                assert result['measurements']['agent_boot_id']==agent.BOOT_ID
        asyncio.run(exercise())
    assert processes and all(p.returncode is not None for p in processes)
    assert not agent.task_store.tasks
    assert not asyncio.run(agent.session_service.list_sessions(app_name='tax_demo' if fiscal else 'markets_demo')).sessions
