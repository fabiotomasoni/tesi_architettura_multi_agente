import json,os,subprocess,sys
from pathlib import Path
from copy import deepcopy
import pytest
from gateway.lab_profile import full_view,FullFinancialView
from gateway.disclosure import view_metrics
from tests.test_mortgage import profile


def run(code,organization='single',policy='disabled',**env):
    return subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env={**os.environ,'TESI_RUNTIME':'local','TESI_EXPERIMENT':organization,'TESI_MINIMIZATION':policy,'TESI_MARKET_SOURCE':'simulated','TESI_TAX_SOURCE':'simulated','TESI_MCP_PROFILE':'nominal',**env})


def test_full_profile_preserves_values_periods_and_ambiguity_without_sources():
    from gateway.pdf_input import extract_profile
    p,_=extract_profile([Path(f'dataset/Documents/C016_{k}.pdf').read_bytes() for k in ('mutuo','interessi')])
    before=p.model_dump();d=full_view(p)['financial_profile']
    assert d['annual_rate']['value']=='ambiguous' and d['annual_rate']['status']=='ambiguous'
    assert d['remaining_months']['value']=='61' and d['annual_interest']['value']=='7836.70'
    assert all(v is None or set(v)=={'value','unit','period','status'} for v in d.values())
    assert p.model_dump()==before
    assert view_metrics(full_view(p),'test')['test_exact_amount_fields']==3


@pytest.mark.parametrize('change',['unknown','pii','source','missing'])
def test_closed_profile_does_not_accept_identifiers_or_text(change):
    d=full_view(profile())
    if change=='unknown':d['financial_profile']['iban']='IT00'
    if change=='pii':d['financial_profile']['remaining_principal']['value']='Mario Rossi'
    if change=='source':d['financial_profile']['remaining_principal']['source']={'quote':'secret'}
    if change=='missing':d['financial_profile'].pop('annual_rate')
    with pytest.raises(ValueError):FullFinancialView.model_validate(d)


@pytest.mark.parametrize('organization',['single','multi'])
def test_disabled_model_uses_whole_financial_context_and_revokes_session(organization):
    r=run('''
import asyncio,json
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone,timedelta
from gateway import runtime
from gateway.pdf_input import extract_profile
from gateway.lab_profile import full_view,FullFinancialView
from gateway.agent_contracts import MarketTask,MarketResult
from gateway.inference import InferenceBroker,InferenceRequest
from gateway.market_evidence import expected_evidence
from gateway.a2a_egress import EgressDenied
from scripts.run_ollama_bridge import validate_payload
runtime.ISOLATED=True
p,_=extract_profile([Path(f'dataset/Documents/C001_{k}.pdf').read_bytes() for k in ('mutuo','interessi')])
view=FullFinancialView.model_validate(full_view(p));sid=uuid4()
broker=InferenceBroker();broker._lab_profiles[sid]=view.model_dump(mode='json')
class Bridge:
 def revoke(self,owner):pass
 async def infer(self,payload,seconds,*,owner=None):
  validate_payload(payload)
  body=json.loads(payload['messages'][1]['content'])
  assert body['context']['financial_profile']['remaining_principal']['value']=='90434.57'
  return {'body':{'message':{'content':'test'},'prompt_eval_count':10,'eval_count':1,'load_duration':0},'ollama_ms':1}
broker.bridge=Bridge()
task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view=view)
async def remote(t):
 await broker.infer(InferenceRequest(correlation_id=t.correlation_id,scenario=t.scenario,evidence=expected_evidence(t.view).model_dump()),'Bearer '+t.inference_token)
 return MarketResult(correlation_id=t.correlation_id,status='completed',evidence=expected_evidence(t.view),summary='test',limits=[],model='llama3.2:3b')
async def test():
 result=await broker.delegate(sid,task,remote)
 assert result.measurements['a2a_view_exact_amount_fields']==3
 broker.revoke(sid);assert not broker._lab_profiles and not broker._grants
 try:await broker.delegate(sid,task,remote)
 except EgressDenied:pass
 else:raise AssertionError('unauthorized full profile accepted')
asyncio.run(test())
''',organization)
    assert r.returncode==0,r.stderr


@pytest.mark.parametrize('policy',['active','disabled'])
def test_view_shape_cannot_be_changed_by_task(policy):
    r=run('''
from uuid import uuid4
from datetime import datetime,timezone,timedelta
from gateway.a2a_egress import authorized_task,EgressDenied
from gateway.agent_contracts import MarketTask
from gateway import runtime
from gateway.lab_profile import full_view
from tests.test_mortgage import profile
minimal={'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}}
wrong=minimal if runtime.UNMINIMIZED else full_view(profile())
t=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view=wrong)
try:authorized_task(t)
except EgressDenied:pass
else:raise AssertionError('wrong view shape accepted')
''',policy=policy);assert r.returncode==0,r.stderr


def test_disabled_cannot_be_enabled_for_demo_or_real_sources():
    for env in ({'TESI_EXPERIMENT':'off'},{'TESI_MARKET_SOURCE':'ecb'},{'TESI_TAX_SOURCE':'ade'}):
        r=run('import gateway.tool_egress',**env);assert r.returncode!=0


def test_corpus_manifest_matches_fixed_pdfs():
    import hashlib
    from gateway.lab_corpus import PDF_CASES
    files=list(Path('dataset/Documents').glob('*.pdf'))
    assert len(files)==len(PDF_CASES)
    assert all(PDF_CASES.get(hashlib.sha256(p.read_bytes()).hexdigest())==p.name.split('_')[0] for p in files)


@pytest.mark.parametrize('organization',['single','multi'])
@pytest.mark.parametrize('policy',['active','disabled'])
def test_laboratory_rejects_unknown_pdfs_and_direct_json(tmp_path,organization,policy):
    keys=['gateway_to_generalist','generalist_to_gateway','bridge'] if organization=='single' else ['gateway_to_markets','gateway_to_tax','markets_to_gateway','tax_to_gateway','bridge']
    identity=tmp_path/'gateway.json';identity.write_text(json.dumps({'role':'gateway','keys':{k:'1'*64 for k in keys}}))
    r=run('''
from fastapi.testclient import TestClient
from pathlib import Path
from gateway.app import app
from gateway.pdf_input import extract_profile
with TestClient(app) as client:
 raw=Path('dataset/Documents/C001_mutuo.pdf').read_bytes()
 assert client.post('/sessions/pdf',files=[('files',('fake.pdf',raw+b'altered','application/pdf'))],data={'scenarios':['S-01']}).status_code==403
 p,_=extract_profile([raw])
 assert client.post('/sessions',json={'scenarios':['S-01'],'profile':p.model_dump(mode='json')}).status_code==403
 good=client.post('/sessions/pdf',files=[('files',('input.pdf',raw,'application/pdf'))],data={'scenarios':['S-01']})
 assert good.status_code==201,good.text
 sid=good.json()['session_id']
 view=client.post(f'/sessions/{sid}/views',json={'scenario':'S-01','recipient':'markets'}).json()['data']
 from gateway import runtime
 assert ('financial_profile' in view)==runtime.UNMINIMIZED
 assert client.delete('/sessions/'+sid).status_code==204
 assert client.get('/health').json()['minimization']==runtime.MINIMIZATION
''',organization,policy,TESI_RUNTIME='isolated',TESI_IDENTITY_FILE=str(identity))
    assert r.returncode==0,r.stderr


def test_factorial_checker_rejects_old_protocol():
    from scripts.check_factorial_pilot import verify
    cells={(o,p):[{'case':'C001','repetition':1,'minimization':p,'experiment':{'policy':p}}] for o in ('single','multi') for p in ('active','disabled')}
    with pytest.raises(ValueError):verify(cells)


@pytest.mark.parametrize('change',[None,'no_growth','leaked_amount'])
def test_factorial_checker_validates_financial_disclosure_contrast(change):
    from scripts.check_factorial_pilot import verify
    cells={}
    for organization in ('single','multi'):
        for policy in ('active','disabled'):
            measurements={'mcp_tool_calls':1,'ollama_calls':1,'a2a_requests':1}
            for boundary in ('a2a_view','mcp_arguments','model_context'):
                measurements.update({boundary+'_bytes':100 if policy=='active' else 999,boundary+'_exact_amount_fields':0 if policy=='active' else 3})
            activities={s:{'status':'completed','measurements':{**measurements,'agent_boot_id':'one' if organization=='single' else s}} for s in ('S-01','S-02')}
            row={'case':'C001','repetition':1,'organization':organization,'minimization':policy,'input_financial_amount_fields':3,'passed':True,'cleanup_verified':True,'automatic_session_closed':True,'model_digest':'fixed','semantic_result_sha256':'same','activities':activities,'coordination':{'a2a_message_sends':1},'experiment':{'organization':organization,'policy':policy,'protocol':'financial-profile-2x2-v1','sources':'fixed_local_fixtures','schedule':'sequential'}}
            cells[organization,policy]=[row]
    if change=='no_growth':cells['single','disabled'][0]['activities']['S-01']['measurements']['model_context_bytes']=90
    if change=='leaked_amount':cells['single','active'][0]['activities']['S-01']['measurements']['mcp_arguments_exact_amount_fields']=1
    assert all(verify(cells).values())==(change is None)


def test_full_profile_schema_covers_all_fixed_cases():
    from gateway.pdf_input import extract_profile
    for i in range(1,26):
        p,_=extract_profile([Path(f'dataset/Documents/C{i:03}_{k}.pdf').read_bytes() for k in ('mutuo','interessi')])
        assert FullFinancialView.model_validate(full_view(p))
