"""Integrazione applicativa controllata; NON prova di isolamento o campagna.

Il test usa la factory nativa, ADK/A2A con trasporto ASGI e MCP stdio con
callback HTTP loopback. Il vincolo container dell'avvio resta intatto nel codice
produttivo ed è coperto dalle verifiche separate di isolamento.
"""
import asyncio,json,socket,threading,time
from contextlib import contextmanager,ExitStack
from pathlib import Path
import httpx,uvicorn
from fastapi.testclient import TestClient
from gateway import runtime,verification_config as config
organization=runtime.EXPERIMENT
runtime.EXPERIMENT='off'
from gateway.app import create_app
app=create_app()
runtime.EXPERIMENT=organization
from gateway.inference import OLLAMA_ENDPOINT
from scripts.run_ollama_bridge import validate_payload
from scripts.check_report_provenance import verify as provenance
from scripts.check_trace import validate as validate_trace
if organization=='single':
    import services.generalist_agent as generalist
    agents={'S-01':generalist.app,'S-02':generalist.app}
else:
    from services.market_agent import app as markets
    from services.tax_agent import app as tax
    agents={'S-01':markets,'S-02':tax}
original=httpx.AsyncClient
model_calls=[]
held={"enabled":False}
class Router(httpx.AsyncBaseTransport):
    async def handle_async_request(self,req):
        if str(req.url)==OLLAMA_ENDPOINT:
            payload=json.loads(req.content);validate_payload(payload)
            data=json.loads(payload['messages'][1]['content']);fiscal='tax-selection' in payload['messages'][0]['content']
            model_calls.append('S-02' if fiscal else 'S-01')
            if held['enabled']:
                held['request']=(json.loads(req.content),req.headers['authorization']) if req.url.path=='/internal/inference' else held.get('request')
                held['entered'].set()
                try:
                    while held['enabled']:await asyncio.sleep(.01)
                finally:held['stopped'].set()
            selection={'schema_version':'tax-selection-1' if fiscal else 'market-selection-1',
                'source_statement_ids':[s['statement_id'] for s in data['statements'] if s['kind']=='source'][:2],
                'context_statement_id':next(s['statement_id'] for s in data['statements'] if s['kind']=='context'),'explanation':''}
            return httpx.Response(200,json={'message':{'content':json.dumps(selection)},'prompt_eval_count':1,'eval_count':1,'load_duration':0})
        if req.url.path=='/internal/inference' and held['enabled']:held['request']=(json.loads(req.content),req.headers['authorization'])
        selected=agents['S-01'] if req.url.port==8001 else agents['S-02'] if req.url.port==8002 else app
        return await httpx.ASGITransport(app=selected).handle_async_request(req)
httpx.AsyncClient=lambda **kw:original(transport=Router(),**kw) if 'transport' not in kw else original(**kw)
import gateway.a2a_egress as egress
egress.httpx.AsyncHTTPTransport=lambda **kw:Router()

@contextmanager
def serve():
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
    server=uvicorn.Server(uvicorn.Config(app,log_level='critical',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    try:
        end=time.monotonic()+5
        while not server.started:
            if time.monotonic()>end:raise RuntimeError('Callback locale non avviata')
            time.sleep(.01)
        import services.tool_client as tools
        tools.GATEWAY_BASE=f'http://127.0.0.1:{sock.getsockname()[1]}'
        yield
    finally:server.should_exit=True;thread.join(5);sock.close()

def execute(client,case='C001',scenarios=('S-01','S-02'),kinds=('mutuo','interessi'),extra=None):
    files=[('files',(k+'.pdf',Path(f'dataset/Documents/{case}_{k}.pdf').read_bytes(),'application/pdf')) for k in kinds]
    if extra is not None:files.append(('files',('negative.pdf',extra,'application/pdf')))
    upload=client.post('/sessions/pdf',files=files,data={'scenarios':list(scenarios)})
    assert upload.status_code==201,upload.status_code
    sid=upload.json()['session_id'];trace_id=upload.json()['trace_id']
    result=client.post(f'/sessions/{sid}/analysis');assert result.status_code==200,result.status_code
    body=result.json();_,problems=provenance(body['report'],Path('dataset/Documents'));assert not problems,problems
    assert client.delete('/sessions/'+sid).status_code==404
    for s,r in [('S-01','markets'),('S-02','tax')]:
        assert client.post('/sessions/'+sid+'/views',json={'scenario':s,'recipient':r}).status_code==404
    trace=client.get('/traces/'+trace_id).json();validate_trace(trace,organization=organization,minimization=runtime.MINIMIZATION)
    assert trace['summary']['trace_complete'] and trace['profile_closed']
    return body,trace


def finalization_checks(client):
    import gateway.app as module
    endpoint=next(r.endpoint for r in app.routes if getattr(r,'path',None)=='/internal/tools/authorize')
    broker=next(c.cell_contents for c in endpoint.__closure__ if hasattr(c.cell_contents,'_grants'))
    initial=(client.get('/health').json()['gateway_boot_id'])
    from concurrent.futures import ThreadPoolExecutor
    for fault in ['cancel','ttl']:
        upload=client.post('/sessions/pdf',files=[('files',(k+'.pdf',Path(f'dataset/Documents/C001_{k}.pdf').read_bytes(),'application/pdf')) for k in ('mutuo','interessi')],data={'scenarios':['S-01','S-02']})
        sid=upload.json()['session_id'];held.update(enabled=True,entered=threading.Event(),stopped=threading.Event(),request=None)
        old_clock=module.monotonic
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(client.post,f'/sessions/{sid}/analysis')
                assert held['entered'].wait(15)
                assert client.post(f'/sessions/{sid}/analysis').status_code==409
                if fault=='ttl':
                    module.monotonic=lambda:old_clock()+1801
                    assert client.post(f'/sessions/{sid}/views',json={'scenario':'S-01','recipient':'markets'}).status_code==404
                else:assert client.delete('/sessions/'+sid).status_code==204
                response=future.result(timeout=15)
                assert response.status_code==409 and response.json()['status']=='cancelled' and 'report' not in response.json()
                assert held['stopped'].wait(5)
        finally:
            held['enabled']=False;module.monotonic=old_clock
        assert not broker._grants and not broker._privacy and not broker._lab_profiles
        saved=held['request']
        assert saved is not None
        assert client.post('/internal/inference',json=saved[0],headers={'Authorization':saved[1]}).status_code==403
        assert client.delete('/sessions/'+sid).status_code==404
        recovered,_=execute(client);assert recovered['status']=='completed'
        assert client.get('/health').json()['gateway_boot_id']==initial
    # Guasto di consegna ASGI dopo la costruzione del report; nessuna ricevuta client.
    upload=client.post('/sessions/pdf',files=[('files',(k+'.pdf',Path(f'dataset/Documents/C001_{k}.pdf').read_bytes(),'application/pdf')) for k in ('mutuo','interessi')],data={'scenarios':['S-01','S-02']})
    sid=upload.json()['session_id'];generated=[]
    import gateway.report as report_module
    old_report=report_module.build_report
    def observe_report(*args,**kw):
        result=old_report(*args,**kw);generated.append(True);return result
    report_module.build_report=observe_report
    async def exercise():
        incoming=asyncio.Queue();await incoming.put({'type':'http.request','body':b'','more_body':False})
        async def send(message):raise ConnectionError('Controlled ASGI delivery failure')
        scope={'type':'http','asgi':{'version':'3.0'},'method':'POST','scheme':'http','path':f'/sessions/{sid}/analysis',
            'raw_path':f'/sessions/{sid}/analysis'.encode(),'query_string':b'', 'headers':[],
            'client':('127.0.0.1',12345),'server':('127.0.0.1',8000),'http_version':'1.1','root_path':''}
        try:await app(scope,incoming.get,send)
        except (Exception,BaseExceptionGroup):pass
    try:asyncio.run(exercise())
    finally:report_module.build_report=old_report
    assert generated and client.delete('/sessions/'+sid).status_code==404
    assert not broker._grants and not broker._privacy and not broker._lab_profiles
    recovered,_=execute(client);assert recovered['status']=='completed'
    assert client.get('/health').json()['gateway_boot_id']==initial

def main():
    profile=config.PROFILE
    with ExitStack() as stack:
        for agent in {id(a):a for a in agents.values()}.values():stack.enter_context(TestClient(agent))
        stack.enter_context(serve())
        client=stack.enter_context(TestClient(app))
        config.PROFILE='nominal';before,_=execute(client);assert before['status']=='completed', {s:(a['status'],a.get('error_code'),a.get('phases')) for s,a in before['activities'].items()}
        config.PROFILE=profile;model_calls.clear();body,trace=execute(client)
        states={s:a['status'] for s,a in body['activities'].items()}
        expected={'S-01':'completed','S-02':'completed'}
        if profile=='source_timeout':expected['S-01']='failed'
        if profile=='source_malformed':expected['S-02']='failed'
        if profile in {'both_unavailable','hostile_result'}:expected={s:'failed' for s in expected}
        if profile in {'metadata','payload_identifier','payload_financial'}:expected={s:'blocked' for s in expected}
        if profile.startswith('card_'):expected={'S-01':'failed','S-02':'failed' if organization=='single' else 'completed'}
        if profile=='missing_market':expected['S-01']='unverified'
        if profile=='both_missing':expected={s:'unverified' for s in expected}
        if profile=='unfaithful_result':expected['S-01']='blocked'
        assert states==expected,(profile,states)
        if profile=='source_timeout':assert body['activities']['S-01']['error_code']=='timeout'
        for s,state in states.items():assert model_calls.count(s)==int(state=='completed' or profile=='unfaithful_result' and s=='S-01')
        report=body['report'];pairs=report['consistency']['comparisons']
        common=[p for p in pairs if {p['left']['observation_id'],p['right']['observation_id']}=={'shared-reference-S-01','shared-reference-S-02'}]
        if profile in {'nominal','conflict_agents','conflict_document','equivalent_units','different_period','different_product'}:
            assert len(common)==1
            status={'conflict_agents':'conflict','different_period':'not_comparable','different_product':'not_comparable'}.get(profile,'consistent')
            assert common[0]['status']==status
            assert all(x['gateway_receipt_verified'] and x['institutional_live_retrieval'] is False for x in report['comparison_references'])
            if profile.startswith('conflict_'):
                assert report['consistency']['unresolved_conflicts']>0
                assert report['mortgage_contract_analysis']['status']=='not_calculated'
                assert report['tax_application']['status']=='not_calculated'
        if profile.startswith('card_'):
            assert trace['summary']['a2a_message_dispatch_attempts']==(0 if organization=='single' else 1)
        if profile in {'payload_identifier','payload_financial'}:
            assert trace['summary']['tool_permits_issued']==0
            assert any(s['phase']=='privacy_scan' and s['outcome']=='blocked' for s in trace['spans'])
            assert 'alice.canary' not in json.dumps(trace)
        if profile=='metadata':assert not any(s['phase']=='source_proxy' for s in trace['spans'])
        if profile=='nominal':
            finalization_checks(client)
            for case in ['C006','C011','C016','C021']:
                b,_=execute(client,case);assert b['status']==('completed' if case=='C021' else 'partial')
            altered=Path('gateway/fixtures/verification_scan.pdf').read_bytes()+b'altered'
            assert client.post('/sessions/pdf',files=[('files',('altered.pdf',altered,'application/pdf'))],data={'scenarios':['S-01']}).status_code==403
            for kind in ['scan','encrypted','corrupt']:
                raw=Path('gateway/fixtures/verification_'+kind+'.pdf').read_bytes()
                response=client.post('/sessions/pdf',files=[('files',('negative.pdf',raw,'application/pdf'))],data={'scenarios':['S-01','S-02']})
                assert response.status_code==400
                trace=client.get('/traces/'+response.headers['x-trace-id']).json()
                assert any(s['phase']=='pdf_prevalidation' for s in trace['spans']) and not trace['profile_created']
            b,_=execute(client,kinds=('mutuo',),extra=Path('gateway/fixtures/verification_corrupt.pdf').read_bytes());assert b['status']=='partial'
            b,_=execute(client,'C006',('S-01',));assert b['status']=='blocked'
            from scripts.evaluation_support import utility
            import gateway.app as app_module
            required=json.loads(Path('evaluation/annotations.json').read_text())['cases'][0]['agent_utility_facts']['S-01']
            original_view=app_module.make_view
            observed_utility=[]
            def too_general(profile,scenario):
                permitted=original_view(profile,scenario)
                if scenario.value=='S-01':
                    data=permitted['data'] if 'data' in permitted else permitted
                    candidate={'rate_type':profile.rate_type.value}
                    observed_utility.append(utility(candidate,required))
                    return candidate
                return permitted
            if runtime.MINIMIZATION=='active':
                app_module.make_view=too_general
                try:reduced,_=execute(client)
                finally:app_module.make_view=original_view
                assert observed_utility and observed_utility[0]['ratio']==.5
                assert reduced['activities']['S-01']['status']=='blocked' and reduced['activities']['S-01']['error_code']=='invalid_view'
                assert reduced['activities']['S-02']['status']=='completed'
            from dataclasses import replace
            from types import MappingProxyType
            import gateway.tool_egress as tools
            from scripts.check_substitution import digest,normalized
            original_routes=tools.TOOL_ROUTES
            try:
                tools.TOOL_ROUTES=MappingProxyType({**original_routes,'S-01':replace(original_routes['S-01'],module='services.rates_mcp_equivalent')})
                replacement,_=execute(client)
            finally:tools.TOOL_ROUTES=original_routes
            restored,_=execute(client)
            assert digest(normalized(before['report']))==digest(normalized(replacement['report']))==digest(normalized(restored['report']))
        config.PROFILE='nominal';recovery,_=execute(client);assert recovery['status']=='completed'
        ids=lambda b:{s:a['result']['measurements']['agent_boot_id'] for s,a in b['activities'].items()}
        assert ids(before)==ids(recovery)
        print(json.dumps({'profile':profile,'organization':organization,'minimization':runtime.MINIMIZATION,
            'scope':'controlled_application_integration_not_container_isolation_or_actual_llm_or_final_campaign',
            'status':body['status'],'cleanup':True,'same_agent_processes':True,'passed':True}))
if __name__=='__main__':main()
