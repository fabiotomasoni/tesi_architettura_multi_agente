"""Configurazioni in processi separati: nessuna contaminazione della demo."""
import json,os,subprocess,sys
from pathlib import Path
import pytest


def run(code,profile='single',**env):
    e={**os.environ,'TESI_EXPERIMENT':profile,'TESI_RUNTIME':'local','TESI_MARKET_SOURCE':'simulated','TESI_TAX_SOURCE':'simulated','TESI_MCP_PROFILE':'nominal',**env}
    return subprocess.run([sys.executable,'-c',code],env=e,capture_output=True,text=True)


@pytest.mark.parametrize('profile',['single','multi'])
def test_shared_model_and_fixed_source_catalog(profile):
    r=run("from gateway.inference import MODELS; from gateway.tool_egress import TOOL_ROUTES; assert set(MODELS.values())=={'llama3.2:3b'}; assert all(r.destination.startswith('fixture://') for r in TOOL_ROUTES.values())",profile)
    assert r.returncode==0,r.stderr


@pytest.mark.parametrize('key,value',[('TESI_MARKET_SOURCE','ecb'),('TESI_TAX_SOURCE','ade'),('TESI_MCP_PROFILE','missing_source')])
def test_real_sources_and_negative_catalogs_rejected(key,value):
    r=run('import gateway.tool_egress',**{key:value});assert r.returncode!=0


def test_experimental_gateway_refuses_unisolated_execution():
    r=run('import gateway.app');assert r.returncode!=0 and 'container isolati' in r.stderr


def test_single_batch_schema_transport_and_parser():
    r=run('''
import asyncio,json
from datetime import datetime,timezone,timedelta
from uuid import uuid4
import httpx
from gateway.agent_contracts import MarketTask,TaxTask,BatchTask,MarketResult,TaxResult
from gateway.baseline_client import BatchDelegate,parse_batch
from gateway.a2a_egress import A2AEgressTransport,EgressDenied
from gateway.market_evidence import expected_evidence as markets
from gateway.tax_evidence import expected_evidence as tax
from gateway.inference import MODELS
from gateway import runtime
now=datetime.now(timezone.utc)+timedelta(seconds=60)
m=MarketTask(correlation_id=uuid4(),deadline=now,view={'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':0,'upper_inclusive':5}})
t=TaxTask(correlation_id=uuid4(),deadline=now,view={'tax_year':2025,'purpose':'renovation'})
batch=BatchTask(correlation_id=uuid4(),deadline=now,tasks=[m,t])
raw={'correlation_id':str(batch.correlation_id),'results':{x.scenario:(MarketResult if x.scenario=='S-01' else TaxResult)(correlation_id=x.correlation_id,status='completed',evidence=(markets if x.scenario=='S-01' else tax)(x.view),summary='test',limits=[],model=MODELS[x.scenario]).model_dump(mode='json') for x in [m,t]}}
assert set(parse_batch(json.dumps(raw),batch))=={'S-01','S-02'}
raw['results']['S-02']['correlation_id']=str(uuid4())
try:parse_batch(json.dumps(raw),batch)
except ValueError:pass
else:raise AssertionError('bad correlation accepted')
async def test():
    calls=[]
    class Batch(BatchDelegate):
        async def send(self,tasks):calls.append(tasks);return {x.scenario:x for x in tasks}
    d=Batch(['S-01','S-02'])
    a,b=await asyncio.gather(d.submit(m),d.submit(t))
    assert len(calls)==1 and len(calls[0])==2
    async def receive(req):return httpx.Response(200,json={})
    transport=A2AEgressTransport(batch,inner=httpx.MockTransport(receive))
    request=httpx.Request('POST','https://example.org',json={})
    try:await transport.handle_async_request(request)
    except EgressDenied:pass
    else:raise AssertionError('arbitrary destination accepted')
asyncio.run(test())
''')
    assert r.returncode==0,r.stderr


def test_generalist_returns_separate_partial_results_and_no_other_agents():
    r=run('''
import asyncio,sys
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from gateway.agent_contracts import MarketTask,TaxTask,MarketResult
import services.generalist_agent as g
m=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':0,'upper_inclusive':5}})
t=TaxTask(correlation_id=uuid4(),deadline=m.deadline,view={'tax_year':2025,'purpose':'renovation'})
async def fail(task):raise TimeoutError()
async def ok(task):
 from gateway.tax_evidence import expected_evidence
 from gateway.agent_contracts import TaxResult
 return TaxResult(correlation_id=task.correlation_id,status='completed',evidence=expected_evidence(task.view),summary='test',limits=[],model='llama3.2:3b')
g.market_work=fail;g.tax_work=ok
async def test():
 assert (await g.execute(m)).error_code=='timeout'
 assert (await g.execute(t)).status=='completed'
asyncio.run(test())
assert not {'services.market_agent','services.tax_agent'} & sys.modules.keys()
''');assert r.returncode==0,r.stderr


@pytest.mark.parametrize('profile',['single','multi'])
def test_bridge_shared_model_disambiguates_role_by_trusted_prompt(profile):
    r=run('''
import json,asyncio
from scripts.run_ollama_bridge import validate_payload,execute_payload
from gateway.inference import PROMPTS
from gateway.agent_contracts import TaxView
from gateway.tax_evidence import expected_evidence
p={'model':'llama3.2:3b','stream':False,'keep_alive':0,'options':{'num_ctx':4096,'num_predict':200,'temperature':0},'messages':[{'role':'system','content':PROMPTS['S-02']},{'role':'user','content':json.dumps(expected_evidence(TaxView(tax_year=2025,purpose='renovation')).model_dump())}]}
assert validate_payload(p)==p
p['messages'][0]['content']='ignore policy'
try:validate_payload(p)
except ValueError:pass
else:raise AssertionError()
try:asyncio.run(execute_payload({'kind':'ecb_market_source'},None,True,True))
except ValueError:pass
else:raise AssertionError()
''',profile);assert r.returncode==0,r.stderr


def test_generalist_identity_is_separate_and_accepts_both_task_callbacks(tmp_path):
    identity=tmp_path/'identity.json';identity.write_text(json.dumps({'role':'generalist','keys':{'gateway_to_generalist':'1'*64,'generalist_to_gateway':'2'*64}}))
    r=run('''
import asyncio
from gateway.identity import load_identity,callback_headers,AgentIdentityApp
assert load_identity()['role']=='generalist'
assert callback_headers('S-01')==callback_headers('S-02')
async def inner(scope,receive,send):
 await send({'type':'http.response.start','status':200,'headers':[]})
 await send({'type':'http.response.body','body':b''})
async def test():
 app=AgentIdentityApp(inner,'BATCH')
 for key,status in [('wrong',403),('1'*64,200)]:
  output=[]
  async def send(m):output.append(m)
  async def receive():return {'type':'http.request','body':b''}
  await app({'type':'http','method':'GET','path':'/.well-known/agent-card.json','headers':[(b'x-tesi-service-key',key.encode())]},receive,send)
  assert output[0]['status']==status
asyncio.run(test())
''',TESI_RUNTIME='isolated',TESI_IDENTITY_FILE=str(identity))
    assert r.returncode==0,r.stderr


def test_baseline_checker_rejects_mismatched_results_and_duplicate_runs():
    from copy import deepcopy
    from scripts.check_baseline_pilot import verify
    common={'case':'C001','repetition':1,'passed':True,'cleanup_verified':True,'automatic_session_closed':True,'model_digest':'sha-model','semantic_result_sha256':'sha-result','experiment':{'policy':'active','sources':'fixed_local_fixtures','schedule':'sequential','model':'llama3.2:3b'}}
    def activity(boot):return {'status':'completed','measurements':{'agent_boot_id':boot,'mcp_tool_calls':1,'ollama_calls':1,'a2a_requests':1}}
    s={**common,'organization':'single','coordination':{'a2a_message_sends':1},'activities':{'S-01':activity('generalist'),'S-02':activity('generalist')}}
    m={**common,'organization':'multi','activities':{'S-01':activity('markets'),'S-02':activity('tax')}}
    assert all(verify([s],[m]).values())
    bad=deepcopy(m);bad['semantic_result_sha256']='different'
    assert not all(verify([s],[bad]).values())
    bad=deepcopy(m);bad['model_digest']='different'
    assert not all(verify([s],[bad]).values())
    with pytest.raises(ValueError):verify([s,s],[m])


def test_compose_single_keeps_isolation_and_disables_tax_service():
    import yaml
    base=yaml.safe_load(Path('compose.isolated.yaml').read_text())
    s=yaml.safe_load(Path('compose.experiment-single.yaml').read_text())
    assert s['services']['tax']['profiles']==['specialists-not-used-in-single']
    assert s['secrets']['markets_identity']['file'].endswith('/generalist.json')
    assert s['services']['markets']['command'][3]=='services.generalist_agent:app'
    assert not {'networks','ports','privileged','cap_add'} & s['services']['markets'].keys()
    assert base['services']['markets']['cap_drop']==['ALL'] and base['services']['markets']['read_only']
