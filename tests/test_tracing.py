"""Misure osservabili e assenza di contenuti; fixture dichiarate, nessun LLM."""
import asyncio
from contextlib import suppress
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from time import sleep
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from gateway.agent_contracts import MarketResult, TaxResult
from gateway.budgets import Budgets, load_budgets
from gateway.market_evidence import expected_evidence as markets
from gateway.tax_evidence import expected_evidence as tax
from gateway.tracing import TraceStore, Span, use_trace, PHASES, METRICS, AGENT_METRICS
from test_cancellation import setup, payload, MODEL_BODY


def uploaded(client, case='C001', scenarios=('S-01','S-02')):
    return client.post('/sessions/pdf',files=[('files',('private-filename.pdf',
        Path(f'dataset/Documents/{case}_{kind}.pdf').read_bytes(),'application/pdf'))
        for kind in ('mutuo','interessi')],data={'scenarios':list(scenarios)})


def safe_trace(trace):
    encoded = json.dumps(trace)
    for forbidden in ('private-filename','inference_token','source_token','"authorization"','Bearer',
                      'remaining_principal','annual_interest','source_quote','summary_for_user',
                      'FICTIONAL_SECRET','MODEL_BODY_SECRET'):
        assert forbidden not in encoded
    assert set(s['phase'] for s in trace['spans']) <= PHASES
    assert all(set(s['metrics'])<=METRICS for s in trace['spans'])
    assert all(s['duration_ms'] is not None and s['duration_ms']>=0 for s in trace['spans'])
    assert trace['summary']['all_spans_finished']


@pytest.mark.parametrize('case,expected,attempts', [('C001','completed',2),('C006','partial',1),('C011','partial',1),('C016','partial',1)])
def test_pdf_to_closed_profile_trace_survives_cleanup_without_values(monkeypatch,case,expected,attempts):
    module = importlib.import_module('gateway.app')
    async def remote(task):
        result_type = MarketResult if task.scenario=='S-01' else TaxResult
        return result_type(correlation_id=task.correlation_id,status='completed',
            evidence=(markets if task.scenario=='S-01' else tax)(task.view),
            summary='summary_for_user MODEL_BODY_SECRET',limits=[],model='controlled',
            measurements={'mcp_ms':2, 'mcp_tool_calls':1, 'FICTIONAL_SECRET':'not copied'})
    monkeypatch.setattr('gateway.market_client.delegate',remote)
    monkeypatch.setattr('gateway.tax_client.delegate',remote)
    with TestClient(module.create_app()) as client:
        response = uploaded(client,case)
        assert response.status_code==201
        body = response.json(); identifier = body['trace_id'];sid=body['session_id']
        assert identifier==response.headers['x-trace-id']
        before = client.get('/traces/'+identifier).json()
        assert not before['profile_closed'] and not before['summary']['trace_complete']
        # Un tempo di lettura dell'utente non è costo di elaborazione.
        sleep(.025)
        result = client.post(f'/sessions/{sid}/analysis')
        assert result.json()['status']==expected
        assert result.json()['trace_id']==identifier
        assert 'trace_id' not in result.json()['report']
        trace = client.get('/traces/'+identifier).json()
        assert trace['profile_closed'] and trace['summary']['trace_complete']
        assert trace['summary']['model_proxy_calls']==0  # remoto sostituito, non fingere una chiamata
        assert trace['summary']['mcp_tool_calls_agent_reported']==attempts
        phases = {s['phase'] for s in trace['spans']}
        assert {'upload','input_read','pdf_prevalidation','extraction','privacy_context',
                'profile_validation','analysis','prepare_task','policy_view',
                'delegate','verify_result','report','presentation','cleanup','asgi_delivery'} <= phases
        if expected=='partial':
            blocked='S-02' if case=='C011' else 'S-01'
            for phase in ('prepare_task','policy_view'):
                observed=[s for s in trace['spans'] if s['phase']==phase and s['outcome']=='blocked']
                assert len(observed)==1 and observed[0]['scenario']==blocked
                assert observed[0]['error_code']=='input_not_ready'
        assert trace['summary']['elapsed_to_last_event_ms'] > trace['summary']['backend_request_union_ms']+15
        assert sum(s['metrics'].get('sessions_removed',0) for s in trace['spans'])==1
        assert client.delete('/sessions/'+sid).status_code==404
        assert client.get('/traces/'+identifier).json()==trace  # sonda tardiva non modifica la prova
        safe_trace(trace)


def test_input_rejected_before_session_still_has_safe_trace():
    module = importlib.import_module('gateway.app')
    with TestClient(module.create_app()) as client:
        response = client.post('/sessions/pdf',files={'files':('FICTIONAL_SECRET',b'not a pdf')},data={'scenarios':['S-01']})
        assert response.status_code==400
        trace = client.get('/traces/'+response.headers['x-trace-id']).json()
        assert trace['profile_created'] is False
        assert trace['summary']['trace_complete']
        assert any(s['phase']=='pdf_prevalidation' and s['outcome']=='failed' for s in trace['spans'])
        safe_trace(trace)
        response = client.post('/sessions/pdf',data={'scenarios':['S-01']})
        assert response.status_code==422
        trace = client.get('/traces/'+response.headers['x-trace-id']).json()
        assert trace['summary']['trace_complete']


@pytest.mark.parametrize('fault', ['timeout','unavailable','cancel'])
def test_model_failure_usage_unknown_then_recovery_same_gateway(setup,fault):
    app, broker, keys, _, _ = setup
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as client:
            response = await client.post('/sessions',json=payload(['S-01']))
            sid, identifier = response.json()['session_id'], response.json()['trace_id']
            running = asyncio.create_task(client.post('/sessions/'+sid+'/analysis'))
            job = await asyncio.wait_for(broker.bridge.poll(),3)
            if fault=='cancel':
                assert (await client.delete('/sessions/'+sid)).status_code==204
            else:
                broker.bridge.complete(job['job_id'],error=fault)
            response = await running
            assert response.status_code==(409 if fault=='cancel' else 200)
            trace = (await client.get('/traces/'+identifier)).json()
            assert trace['profile_closed'] and trace['summary']['trace_complete']
            assert trace['summary']['prompt_tokens'] is None and trace['summary']['output_tokens'] is None
            assert trace['summary']['model_proxy_calls']==1 and trace['summary']['model_usage_observed']==0
            assert trace['summary']['tool_permits_issued']==1
            assert any(s['phase']=='bridge_wait' and s['metrics']['bridge_claimed']==1 for s in trace['spans'])
            root = next(s for s in trace['spans'] if s['phase']=='analysis')
            assert root['outcome']==('cancelled' if fault=='cancel' else 'failed')
            safe_trace(trace)
            assert not broker._privacy and not broker._grants and not broker.bridge.pending
            response = await client.post('/sessions',json=payload(['S-01']))
            next_id, next_sid = response.json()['trace_id'], response.json()['session_id']
            running = asyncio.create_task(client.post('/sessions/'+next_sid+'/analysis'))
            job = await asyncio.wait_for(broker.bridge.poll(),3)
            broker.bridge.complete(job['job_id'],body=MODEL_BODY,ollama_ms=1)
            response = await running
            assert response.json()['status']=='completed'
            recovered = (await client.get('/traces/'+next_id)).json()
            assert recovered['gateway_boot_id']==trace['gateway_boot_id']
            assert recovered['summary']['prompt_tokens']==1 and recovered['summary']['output_tokens']==1
            assert recovered['summary']['trace_complete']
    asyncio.run(exercise())


def test_boundaries_do_not_allow_free_text_and_store_is_bounded(monkeypatch):
    store = TraceStore(uuid4().hex,capacity=2,max_spans=2,ttl=1)
    first = store.create()
    with use_trace(first):
        with Span('upload') as span:
            with pytest.raises(ValueError):span.metric(prompt_tokens='FICTIONAL_SECRET')
            with pytest.raises(ValueError):span.metric(unknown=3)
            with pytest.raises(ValueError):span.metric(ollama_ms=float('nan'))
            with pytest.raises(ValueError):Span('FICTIONAL_SECRET')
            with Span('extraction'):pass
            with Span('cleanup'):pass
    assert store.snapshot(first[1])['truncated']
    assert not store.snapshot(first[1])['summary']['trace_complete']
    store.create();store.create()
    assert store.snapshot(first[1]) is None
    import gateway.tracing as module
    monkeypatch.setattr(module,'monotonic',lambda:10**12)
    assert not store.snapshot(next(iter(store._records)))


@pytest.mark.parametrize('value', ['NaN','inf','0','-1','3601','abc'])
def test_budget_rejects_invalid_values(value):
    with pytest.raises(RuntimeError):load_budgets({'TESI_ACTIVITY_TIMEOUT_SECONDS':value})


@pytest.mark.parametrize('organization',['single','multi'])
def test_experiment_budgets_are_fixed(organization):
    assert load_budgets({'TESI_EXPERIMENT':organization})==Budgets()
    with pytest.raises(RuntimeError):load_budgets({'TESI_EXPERIMENT':organization,'TESI_MODEL_TIMEOUT_SECONDS':'1'})


def test_configured_deadline_stops_graph_without_waiting_120_seconds(monkeypatch):
    from gateway.workflow import run_workflow
    import gateway.workflow as module
    monkeypatch.setattr(module,'BUDGETS',Budgets(.02,.01,.01,.01))
    async def remote(task):await asyncio.sleep(5)
    def view():return {'data':{'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}}}
    closed = []
    result=asyncio.run(asyncio.wait_for(run_workflow(view,remote,lambda:closed.append(True)),1))
    assert result['error_code']=='timeout' and closed==[True]


def test_traces_lost_on_new_app_boot():
    module = importlib.import_module('gateway.app')
    with TestClient(module.create_app()) as first:
        response = uploaded(first)
        identifier=response.json()['trace_id']
        first.delete('/sessions/'+response.json()['session_id'])
        boot=first.get('/traces/'+identifier).json()['gateway_boot_id']
    with TestClient(module.create_app()) as second:
        assert second.get('/traces/'+identifier).status_code==404
        assert str(second.get('/health').json()['gateway_boot_id'])!=boot


def test_manual_checker_with_real_a2a_mcp_and_injected_model_faults(monkeypatch,local_gateway):
    """Solo topologia nativa e inferenza sono fixture; A2A/MCP sono reali."""
    # Un processo fresco evita il riuso, da altri test, di lock ADK/A2A
    # legati a event loop già chiusi. Tutte le fasi di questa prova usano
    # gli stessi processi/avvii, inclusi guasti e recupero.
    if os.environ.get('TESI_TRACE_FRESH_TEST_PROCESS')!='1':
        completed=subprocess.run([sys.executable,'-m','pytest','-q',
            'tests/test_tracing.py::test_manual_checker_with_real_a2a_mcp_and_injected_model_faults','--tb=short'],
            env={**os.environ,'TESI_TRACE_FRESH_TEST_PROCESS':'1'},capture_output=True,text=True,timeout=75)
        assert completed.returncode==0,completed.stdout+completed.stderr
        return
    import dataclasses
    import gateway.a2a_egress as a2a
    import gateway.market_client as market_client
    import gateway.tax_client as tax_client
    import services.market_agent as market_agent
    import services.tax_agent as tax_agent
    import services.tool_client as tools
    import services.inference_client as inference_client
    from gateway.inference import InferenceBroker, OLLAMA_ENDPOINT, MODELS
    from gateway.ollama_bridge import OllamaBridge
    from scripts.check_trace import TraceDemo, check
    module=importlib.import_module('gateway.app')
    broker=InferenceBroker()
    monkeypatch.setattr(module,'InferenceBroker',lambda:broker)
    original=httpx.AsyncClient
    class Transport(httpx.AsyncBaseTransport):
        def __init__(self):self.inner=httpx.AsyncHTTPTransport(trust_env=False)
        async def handle_async_request(self,request):
            if str(request.url)==OLLAMA_ENDPOINT:
                body=json.loads(request.content)
                scenario=next(s for s,m in MODELS.items() if m==body['model'])
                token=next(k for k,g in broker._grants.items() if g.task.scenario==scenario and g.used and not g.completed)
                reply=await broker.bridge.infer(body,10,owner=token)
                return httpx.Response(200,json=reply['body'])
            assert request.url.host=='127.0.0.1'
            return await self.inner.handle_async_request(request)
        async def aclose(self):await self.inner.aclose()
    def client_factory(*args,**kwargs):
        if 'transport' not in kwargs:kwargs['transport']=Transport()
        return original(*args,**kwargs)
    monkeypatch.setattr(httpx,'AsyncClient',client_factory)
    app=module.create_app();broker.bridge=OllamaBridge()
    with local_gateway(market_agent.app) as m,local_gateway(tax_agent.app) as t,local_gateway(app) as base:
        monkeypatch.setattr(market_agent.card,'url',m+'/');monkeypatch.setattr(tax_agent.card,'url',t+'/')
        routes={**a2a.ROUTES,'S-01':dataclasses.replace(a2a.ROUTES['S-01'],endpoint=m+'/'),
                'S-02':dataclasses.replace(a2a.ROUTES['S-02'],endpoint=t+'/')}
        monkeypatch.setattr(a2a,'ROUTES',routes)
        for client,scenario in [(market_client,'S-01'),(tax_client,'S-02')]:
            monkeypatch.setattr(client,'ROUTES',routes)
            monkeypatch.setattr(client,'ENDPOINT',routes[scenario].endpoint)
        monkeypatch.setattr(tools,'GATEWAY_BASE',base)
        monkeypatch.setattr(inference_client,'GATEWAY_ENDPOINT',base+'/internal/inference')
        class NativeLab(TraceDemo):
            async def health(self):
                response=await self.client.get('/health');response.raise_for_status()
                assert response.json()['experiment']=='off' and response.json()['market_source']=='simulated'
                return response.json()['gateway_boot_id']
        async def exercise():
            async with original(base_url=base,trust_env=False,timeout=20) as client:
                result=await asyncio.wait_for(check(NativeLab(client,'unused-native-fixture')),60)
                assert result['passed'],[k for k,v in result['checks'].items() if not v]
                assert len(result['rows'])==6
                for row in result['rows']:safe_trace(row['trace'])
        asyncio.run(exercise())
    assert not broker._grants and not broker._privacy and not broker.bridge.pending
    assert not market_agent.task_store.tasks and not tax_agent.task_store.tasks


def test_host_http_observation_retains_failed_response_without_payload(monkeypatch):
    from gateway.http_observation import observe_execution, validate_execution
    from scripts.run_ollama_bridge import execute_payload
    from gateway.inference import PROMPTS
    from gateway.agent_contracts import MarketView
    from gateway.market_evidence import expected_evidence
    evidence=expected_evidence(MarketView(mortgage_type='not_specified',rate_type='fixed',remaining_years_band={'lower_exclusive':5,'upper_inclusive':10}))
    request={'model':'llama3.2:3b','stream':False,'keep_alive':0,
             'options':{'num_ctx':4096,'num_predict':200,'temperature':0},
             'messages':[{'role':'system','content':PROMPTS['S-01']},{'role':'user','content':json.dumps(evidence.model_dump(mode='json'))}]}
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(502,text='MODEL_BODY_SECRET'))) as client:
            with observe_execution() as observation:
                with pytest.raises(httpx.HTTPStatusError):await execute_payload(request,client)
            assert observation=={'kind':'ollama','dispatch_attempts':1,'responses_observed':1}
            validate_execution(observation,'inference')
            assert 'MODEL_BODY_SECRET' not in json.dumps(observation)
    asyncio.run(exercise())


def test_trace_endpoint_is_not_available_to_agent_identity(setup):
    app,_,keys,_,_=setup
    with TestClient(app) as client:
        response=uploaded(client)
        identifier=response.json()['trace_id']
        denied=client.get('/traces/'+identifier,headers={'x-tesi-service-key':keys['markets_to_gateway']})
        assert denied.status_code==403
        assert client.get('/traces/'+identifier).status_code==200


def test_denied_source_replay_does_not_recount_prior_http_receipt():
    from datetime import datetime, timedelta, timezone
    from gateway.agent_contracts import MarketTask
    from gateway.inference import Grant, InferenceBroker
    from gateway.tool_egress import SourceRequest, source_request
    from gateway.a2a_egress import EgressDenied
    store=TraceStore(uuid4().hex);selected=store.create()
    task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=30),
        view={'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
    broker=InferenceBroker()
    # Ricevuta preesistente: il replay non esegue un secondo recupero.
    grant=Grant(uuid4(),task,source_token='controlled-capability',source_used=True,
                external_http_requests=1,external_http_ms=1,trace_context=selected)
    broker._grants['controlled-owner']=grant
    request=SourceRequest(correlation_id=task.correlation_id,scenario=task.scenario,
        tool='lookup_rates',arguments=task.view.model_dump(mode='json'),destination='fixture://simulated-rates-v1',headers={})
    with pytest.raises(EgressDenied):asyncio.run(source_request(broker,request,'Bearer controlled-capability'))
    trace=store.snapshot(selected[1])
    assert trace['summary']['callback_denials']==1
    assert trace['summary']['source_http_success_receipts']==0
    assert all('source_http_success_receipts' not in s['metrics'] for s in trace['spans'])


@pytest.mark.parametrize('error,category', [
    (ValueError('Incarichi non ricevuti: controllare agenti e arresto del ponte ordinario.'),'model_job_not_received'),
    (ValueError('FICTIONAL_SECRET MODEL_BODY_SECRET'),'invalid_response'),
    (TimeoutError('FICTIONAL_SECRET'),'timeout'),
    (httpx.HTTPStatusError('FICTIONAL_SECRET',request=httpx.Request('GET','http://test/FICTIONAL_SECRET'),
                           response=httpx.Response(403,text='MODEL_BODY_SECRET')),'http_error'),
])
def test_failed_trace_pilot_preserves_evidence_without_leaking_exception_text(monkeypatch,error,category):
    import scripts.check_trace as module
    lab=module.TraceDemo(None,'not_exported_credential')
    async def fail(collector):
        collector.label='recovery';collector.stage='claim_model'
        collector.checks['nominal/outcome']=True
        # Nessun dato di profilo: evidenza parziale già validata dal driver.
        collector.rows.append({'label':'nominal','case':'C001'})
        raise error
    monkeypatch.setattr(module,'check',fail)
    result=asyncio.run(module.run_checked(lab))
    assert result['passed'] is False and result['checks']=={'nominal/outcome':True}
    assert result['rows']==[{'label':'nominal','case':'C001'}]
    assert result['failure']['label']=='recovery' and result['failure']['stage']=='claim_model'
    assert result['failure']['category']==category
    if category=='http_error':assert result['failure']['http_status']==403
    for secret in ('FICTIONAL_SECRET','MODEL_BODY_SECRET','not_exported_credential'):
        assert secret not in json.dumps(result)
