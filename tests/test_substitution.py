"""V-06: contratto e sostituzione positiva su A2A/MCP reali, modello controllato."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest

from scripts.check_substitution import CASES, MODULES, NAMES, SubstitutionDemo, compare, digest, normalized, schema, code_digest

ROOT = Path(__file__).resolve().parents[1]


def run_config(code, implementation, **extra):
    env={**os.environ,'TESI_RUNTIME':'local','TESI_EXPERIMENT':'off','TESI_MINIMIZATION':'active',
         'TESI_MARKET_SOURCE':'simulated','TESI_TAX_SOURCE':'simulated','TESI_MCP_PROFILE':'nominal',
         'TESI_MARKET_TOOL_IMPLEMENTATION':implementation,'LANGSMITH_TRACING':'false',**extra}
    return subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=15)


@pytest.mark.parametrize('implementation',['standard','equivalent'])
def test_selected_catalog_authorizes_only_its_implementation(implementation):
    result=run_config('''
import asyncio
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from uuid import uuid4
from gateway.agent_contracts import MarketTask
from gateway.a2a_egress import EgressDenied
from gateway.inference import InferenceBroker
from gateway.tool_egress import TOOL_ROUTES,ToolRequest,authorize_tool
broker=InferenceBroker();selected=TOOL_ROUTES['S-01'].module
assert TOOL_ROUTES['S-02'].module=='services.tax_mcp'
async def remote(task):
 request=ToolRequest(correlation_id=task.correlation_id,scenario='S-01',tool='lookup_rates',arguments=task.view.model_dump(mode='json'),server_module='services.rates_mcp_equivalent' if selected=='services.rates_mcp' else 'services.rates_mcp')
 try:authorize_tool(broker,request,'Bearer '+task.inference_token)
 except EgressDenied:pass
 else:raise AssertionError('Modulo non selezionato ammesso')
 request.server_module=None
 permit=authorize_tool(broker,request,'Bearer '+task.inference_token)
 assert permit.module==selected
 return SimpleNamespace(measurements={})
task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=10),view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
r=asyncio.run(broker.delegate(uuid4(),task,remote))
assert r.measurements['gateway_tool_module']==selected and r.measurements['tool_catalog_version']=='0.4.0'
assert not broker._grants
''',implementation)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('implementation,extra',[
    ('services.rates_mcp_equivalent',{}),('unconfigured',{}),
    ('equivalent',{'TESI_EXPERIMENT':'single'}),('equivalent',{'TESI_EXPERIMENT':'multi'}),
    ('equivalent',{'TESI_MCP_PROFILE':'missing_source'}),
    ('equivalent',{'TESI_RUNTIME':'isolated','TESI_MARKET_SOURCE':'ecb'}),
    ('equivalent',{'TESI_RUNTIME':'isolated','TESI_TAX_SOURCE':'ade'}),
])
def test_unapproved_configuration_combinations_are_refused(implementation,extra):
    result=run_config('import gateway.tool_egress',implementation,**extra)
    assert result.returncode!=0


def test_real_stdio_servers_have_same_contract_and_do_not_invent_without_proxy():
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def exercise():
        specs={key:await schema(module) for key,module in MODULES.items()}
        assert specs['standard']['tool_contracts']==specs['equivalent']['tool_contracts']
        assert {v['server_name'] for v in specs.values()}==set(NAMES.values())
        for module in MODULES.values():
            async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m',module])) as streams:
                async with ClientSession(*streams) as client:
                    await client.initialize()
                    result=await client.call_tool('lookup_rates',{'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
                    assert not result.isError
                    assert json.loads(result.content[0].text)=={'status':'blocked','error_code':'not_authorized'}
                    mixed=await client.call_tool('lookup_rates',{'mortgage_type':'other','financial_profile':{}})
                    assert mixed.isError
    asyncio.run(exercise())


def test_normalization_changes_only_allocated_document_identifiers():
    def snapshot(identifier):
        return {'document_data':[{'source':{'document_id':identifier,'document_sha256':'a'*64,'quote':'1.000,00 EUR'},
                                  'value':'1000.00','unit':'EUR','period':'2025-12-31','status':'validated'}],
                'source_ref':identifier+'#page/1','limits':['Simulato'],'document_html':identifier}
    first=snapshot('doc-one');second=snapshot('doc-two')
    assert normalized(first)==normalized(second)
    for key,value in [('value','1001.00'),('unit','USD'),('period','2024-12-31'),('status','ambiguous')]:
        altered=snapshot('doc-two');altered['document_data'][0][key]=value
        assert digest(normalized(first))!=digest(normalized(altered))
    changed=snapshot('doc-two');changed['document_data'][0]['source']['quote']='2.000,00 EUR'
    assert normalized(first)!=normalized(changed)
    changed=snapshot('doc-two');changed['limits']=[]
    assert normalized(first)!=normalized(changed)
    with pytest.raises(ValueError):normalized({'source':{'document_id':'doc-one'}})


@pytest.mark.parametrize('fault',['configure','execution'])
def test_checker_restores_standard_and_cleans_local_requests_on_failure(monkeypatch,fault):
    import scripts.check_substitution as checker
    class Controller:
        flag='standard';calls=[]
        async def configure(self,flag):
            self.calls.append(flag);self.flag=flag
            if flag=='equivalent' and fault=='configure':raise ValueError('Controlled config failure')
        async def images(self):return {'gateway':'controlled','markets':'controlled','tax':'controlled'}
    controller=Controller()
    class Lab:
        cleaned=False
        client=None
        async def health(self):return '0'*32
        async def get(self,*args):
            return httpx.Response(200,json={'market_tool_implementation':controller.flag,'tool_catalog_version':'0.4.0'})
        async def run_case(self,case,implementation):
            if implementation=='equivalent':raise ValueError('Controlled execution failure')
            return {'case':case,'passed':True}
        async def cleanup(self):self.cleaned=True
    lab=Lab();lab.client=lab
    async def schemas(module):
        key=next(k for k,v in MODULES.items() if v==module)
        return {'server_name':NAMES[key],'tool_contracts':[{'name':'lookup_rates'}]}
    monkeypatch.setattr(checker,'schema',schemas)
    with pytest.raises(ValueError):asyncio.run(checker.check(lab,controller))
    assert controller.calls==['equivalent','standard'] and controller.flag=='standard'
    assert lab.cleaned


# Solo fixture di indirizzamento loopback e del modello: le implementazioni MCP
# sono scelte dal vero flag di avvio, mai sostituite con monkeypatch nel gateway.
NATIVE_GATEWAY = r'''
import dataclasses,os,json,importlib
import httpx,uvicorn
import gateway.a2a_egress as a2a
import gateway.market_client as markets
import gateway.tax_client as tax
from gateway.inference import OLLAMA_ENDPOINT,InferenceBroker,MODELS
from gateway.ollama_bridge import OllamaBridge
broker=InferenceBroker()
routes=dict(a2a.ROUTES)
for scenario,key in [('S-01','TESI_TEST_MARKETS'),('S-02','TESI_TEST_TAX')]:
 routes[scenario]=dataclasses.replace(routes[scenario],endpoint=os.environ[key]+'/')
a2a.ROUTES=routes
markets.ROUTES=tax.ROUTES=routes
markets.ENDPOINT=routes['S-01'].endpoint;tax.ENDPOINT=routes['S-02'].endpoint
original=httpx.AsyncClient
class Transport(httpx.AsyncBaseTransport):
 def __init__(self):self.inner=httpx.AsyncHTTPTransport(trust_env=False)
 async def handle_async_request(self,request):
  if str(request.url)==OLLAMA_ENDPOINT:
   payload=json.loads(request.content)
   scenario=next(s for s,m in MODELS.items() if m==payload['model'])
   token=next(k for k,g in broker._grants.items() if g.task.scenario==scenario and g.used and not g.completed)
   reply=await broker.bridge.infer(payload,10,owner=token)
   return httpx.Response(200,json=reply['body'])
  assert request.url.host=='127.0.0.1'
  return await self.inner.handle_async_request(request)
 async def aclose(self):await self.inner.aclose()
def client(**kwargs):
 if 'transport' not in kwargs:kwargs['transport']=Transport()
 return original(**kwargs)
httpx.AsyncClient=client
module=importlib.import_module('gateway.app')
module.InferenceBroker=lambda:broker
app=module.create_app();broker.bridge=OllamaBridge()
uvicorn.run(app,fd=int(os.environ['TESI_TEST_FD']),log_level='critical',access_log=False,proxy_headers=False)
'''


@pytest.mark.skipif(os.name=='nt',reason='Fixture nativa POSIX con fd condiviso; Docker Windows previsto separatamente')
def test_configuration_only_substitution_through_real_a2a_and_mcp_preserves_complete_reports(monkeypatch,local_gateway):
    import services.market_agent as markets
    import services.tax_agent as tax
    import services.tool_client as tools
    import services.inference_client as inference
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
    base='http://127.0.0.1:'+str(sock.getsockname()[1])
    monkeypatch.setattr(tools,'GATEWAY_BASE',base)
    monkeypatch.setattr(inference,'GATEWAY_ENDPOINT',base+'/internal/inference')
    phases={}
    try:
        with local_gateway(markets.app) as m,local_gateway(tax.app) as t:
            monkeypatch.setattr(markets.card,'url',m+'/');monkeypatch.setattr(tax.card,'url',t+'/')
            for phase,implementation in [('reference','standard'),('replacement','equivalent'),('restored','standard')]:
                env={**os.environ,'TESI_RUNTIME':'local','TESI_EXPERIMENT':'off','TESI_MINIMIZATION':'active',
                    'TESI_MARKET_SOURCE':'simulated','TESI_TAX_SOURCE':'simulated','TESI_MCP_PROFILE':'nominal',
                    'TESI_MARKET_TOOL_IMPLEMENTATION':implementation,'TESI_TEST_FD':str(sock.fileno()),
                    'TESI_TEST_MARKETS':m,'TESI_TEST_TAX':t,'LANGSMITH_TRACING':'false','PYTHONDONTWRITEBYTECODE':'1'}
                process=subprocess.Popen([sys.executable,'-c',NATIVE_GATEWAY],cwd=ROOT,env=env,pass_fds=(sock.fileno(),),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                try:
                    until=time.monotonic()+10
                    with httpx.Client(base_url=base,timeout=.5,trust_env=False) as client:
                        while True:
                            try:
                                h=client.get('/health')
                                if h.status_code==200:break
                            except httpx.HTTPError:pass
                            assert process.poll() is None and time.monotonic()<until,'Gateway della fixture non avviato'
                            time.sleep(.02)
                    async def run_cases():
                        async with httpx.AsyncClient(base_url=base,timeout=20,trust_env=False) as client:
                            lab=SubstitutionDemo(client,'not-used-native-fixture')
                            rows=[]
                            try:
                                for case in CASES:
                                    row=await lab.run_case(case,implementation)
                                    assert row['passed'],{key:value for key,value in row['checks'].items() if not value}
                                    rows.append(row)
                                return rows
                            finally:await lab.cleanup()
                    rows=asyncio.run(run_cases());health=h.json()
                    phases[phase]={'implementation':implementation,'gateway_boot_id':health['gateway_boot_id'],
                        'images':{'scope':'native_test_not_docker'},'settings':{k:v for k,v in health.items() if k not in {'gateway_boot_id','market_tool_implementation'}},
                        'code_sha256':code_digest(),'rows':rows}
                finally:
                    process.terminate()
                    try:process.wait(5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(5)
        checks=compare(phases)
        assert all(checks.values()),[k for k,v in checks.items() if not v]
        assert not markets.task_store.tasks and not tax.task_store.tasks
    finally:sock.close()
