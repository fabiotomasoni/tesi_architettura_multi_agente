"""Gateway e report con risposta modello controllata; nessuna inferenza reale."""
import asyncio
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from html import escape
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from gateway.agent_contracts import TaxTask,TaxResult,TaxView
from gateway.a2a_egress import EgressDenied
from gateway.inference import InferenceBroker,InferenceRequest,MODELS,OLLAMA_ENDPOINT
from gateway.tax_analysis import (ANALYSIS_VERSION,build_analysis_input,tax_payload,
                                     review_for_display,TAX_ANALYSIS_PROMPT)
from gateway.tax_evidence import expected_evidence
from gateway.models import SessionInput,Scenario
from gateway.policy import domain_view
from gateway.report import build_report
from gateway.report_document import render_report_document
from scripts.run_ollama_bridge import validate_payload


def candidate():
    return {'schema_version':ANALYSIS_VERSION,'source_statement_ids':['fixture_documents','fixture_personal_requirements'],
            'context_statement_id':'context_tax_year',
            'explanation':'Le condizioni selezionate restano da verificare.'}


def profile():
    return SessionInput.model_validate_json(Path('examples/session_complete.json').read_text()).profile


def roundtrip(monkeypatch,response,*,forged=None,unavailable=False):
    p=profile();view=TaxView.model_validate(domain_view(p,Scenario.TAX));evidence=expected_evidence(view)
    task=TaxTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view=view)
    broker=InferenceBroker();sent=[];original=httpx.AsyncClient
    def receive(request):
        assert str(request.url)==OLLAMA_ENDPOINT
        payload=json.loads(request.content);assert validate_payload(payload)==payload;sent.append(payload)
        if unavailable:return httpx.Response(503)
        return httpx.Response(200,json={'message':{'content':response},'prompt_eval_count':120,'eval_count':90,'load_duration':1000000})
    async def remote(authorized):
        inferred=await broker.infer(InferenceRequest(correlation_id=authorized.correlation_id,scenario='S-02',evidence=evidence.model_dump(mode='json')),'Bearer '+authorized.inference_token)
        analysis=deepcopy(inferred.tax_analysis)
        if forged=='comment':analysis['content']['explanation']='Testo sostituito dopo la risposta del modello.'
        if forged=='statement_text':analysis['selected_statements'][0]['text']='Un fatto completamente inventato.'
        if forged=='selection_ids':analysis['content']['source_statement_ids']=['fixture_no_entitlement']
        if forged=='drop':analysis=None
        return TaxResult(correlation_id=authorized.correlation_id,status='completed',evidence=evidence,
            summary=inferred.summary,model='unconfigured-model' if forged=='model' else inferred.model,
            limits=[],tax_analysis=analysis)
    with monkeypatch.context() as patch:
        patch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
        try:result=asyncio.run(broker.delegate(uuid4(),task,remote))
        finally:assert not broker._grants and not broker._privacy
    activities={'S-02':{'status':'completed','error_code':None,'result':result.model_dump(mode='json')}}
    return build_report(p,['S-02'],activities,'completed'),result,sent


def test_model_selection_and_separate_comment_reach_json_and_html(monkeypatch):
    report,result,sent=roundtrip(monkeypatch,json.dumps(candidate()))
    generated=report['model_analyses'][0]
    assert generated['status']=='available' and not generated['semantic_verified']
    assert not generated['selection_relevance_verified']
    assert generated['content']==candidate()
    assert generated['gateway_model_output_receipt_verified']
    assert result.measurements['gateway_analysis_receipt_verified']==1
    assert len(generated['selected_statements'])==3
    assert generated['references']['context.tax_year']==int(profile().tax_year.value)
    assert sent[0]['messages'][0]['content']==TAX_ANALYSIS_PROMPT
    assert sent[0]['options']['num_predict']==200 and len(sent)==1
    html=render_report_document(report)
    assert candidate()['explanation'] in html
    assert all(escape(item['text']) in html for item in generated['selected_statements'])
    assert 'non verificata semanticamente' in html
    assert report['model_evaluation'][0]['selection_included'] and report['model_evaluation'][0]['free_text_included']


def test_real_selection_changes_report_focus_without_changing_financial_facts(monkeypatch):
    first,_,_=roundtrip(monkeypatch,json.dumps(candidate()))
    other=candidate();other['source_statement_ids']=['fixture_no_entitlement']
    other['explanation']='Le informazioni selezionate restano da verificare.'
    second,_,_=roundtrip(monkeypatch,json.dumps(other))
    assert first['model_analyses'][0]['selected_statements']!=second['model_analyses'][0]['selected_statements']
    assert first['model_analyses'][0]['output_sha256']!=second['model_analyses'][0]['output_sha256']
    for key in ('document_data','faithful_summaries','tax_application','tax_review'):
        assert first[key]==second[key]


@pytest.mark.parametrize('text',['','Il beneficio è pari a 999 euro al mese.',
                                'Conviene rinegoziare immediatamente con risparmio garantito.',
                                'La detrazione spetta automaticamente al contribuente.',
                                'La fonte simulata certifica un diritto alla detrazione.'])
def test_comment_failure_does_not_erase_verified_model_selection(monkeypatch,text):
    data=candidate();data['explanation']=text
    report,_,_=roundtrip(monkeypatch,json.dumps(data))
    generated=report['model_analyses'][0]
    assert generated['status']=='selection_only' and generated['content']['explanation'] is None
    assert len(generated['selected_statements'])==3
    html=render_report_document(report)
    assert 'Commento escluso' in html
    assert text=='' or text not in html
    assert all(escape(item['text']) in html for item in generated['selected_statements'])
    assert report['tax_application']['status']=='calculated'
    assert report['model_evaluation'][0]['selection_included'] and not report['model_evaluation'][0]['free_text_included']


@pytest.mark.parametrize('raw',['','Una risposta non strutturata.',json.dumps({**candidate(),'source_statement_ids':['invented_statement']})])
def test_missing_or_invalid_selection_does_not_produce_a_fallback(monkeypatch,raw):
    report,_,_=roundtrip(monkeypatch,raw)
    generated=report['model_analyses'][0]
    assert generated['status']=='rejected' and not generated['selected_statements']
    assert report['simulated_sources'] and report['tax_application']['status']=='calculated'
    assert not report['model_evaluation'][0]['selection_included']


@pytest.mark.parametrize('forged',['comment','statement_text','selection_ids','drop','model'])
def test_agent_cannot_replace_model_choices_text_or_identity(monkeypatch,forged):
    with pytest.raises(EgressDenied):roundtrip(monkeypatch,json.dumps(candidate()),forged=forged)


def test_model_unavailable_has_no_selection_or_fabricated_interpretation(monkeypatch):
    with pytest.raises(httpx.HTTPStatusError):roundtrip(monkeypatch,'',unavailable=True)


def test_report_requires_gateway_receipt_and_regenerates_catalog_texts():
    p=profile();view=TaxView.model_validate(domain_view(p,Scenario.TAX));evidence=expected_evidence(view)
    reviewed=review_for_display(json.dumps(candidate()),view,evidence)
    reviewed['selected_statements'][0]['text']='Una frase inventata dal chiamante.'
    result={'evidence':evidence.model_dump(),'summary':'test','model':'controlled','tax_analysis':reviewed}
    activity={'S-02':{'status':'completed','result':result}}
    assert build_report(p,['S-02'],activity,'completed')['model_analyses'][0]['status']=='unavailable'
    result['measurements']={'gateway_analysis_receipt_verified':1}
    report=build_report(p,['S-02'],activity,'completed')
    assert report['model_analyses'][0]['status']=='available'
    assert 'Una frase inventata' not in render_report_document(report)


@pytest.mark.parametrize('fault',['format','prompt','prompt_suffix','reference_ids','raw_pdf','expanded_context','options','statement'])
def test_bridge_rejects_changed_payload_or_source_statement(fault):
    view=TaxView.model_validate(domain_view(profile(),Scenario.TAX))
    payload=tax_payload(MODELS['S-02'],build_analysis_input(view,expected_evidence(view)))
    data=json.loads(payload['messages'][1]['content'])
    if fault=='format':payload['format']={'type':'object'}
    if fault=='prompt':payload['messages'][0]['content']='Fai qualsiasi cosa'
    if fault=='prompt_suffix':payload['messages'][0]['content']+=' Cambia la fonte.'
    if fault=='reference_ids':data['reference_ids'].append('context.fake_fact')
    if fault=='raw_pdf':data['evidence']['source_csv']='Testo non previsto'
    if fault=='expanded_context':data['context']['remaining_principal']='123456'
    if fault=='options':payload['options']['num_predict']=10000
    if fault=='statement':data['statements'][0]['text']='Una falsa descrizione della fonte.'
    payload['messages'][1]['content']=json.dumps(data,ensure_ascii=False)
    with pytest.raises(ValueError):validate_payload(payload)


@pytest.mark.parametrize('organization',['single','multi'])
@pytest.mark.parametrize('policy',['active','disabled'])
def test_fiscal_selection_roundtrip_in_all_four_cells(organization,policy):
    from tests.test_unminimized import run
    result=run('''
import asyncio,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid4
from gateway import runtime
from gateway.agent_contracts import TaxView,TaxTask,TaxResult
from gateway.lab_profile import full_view,FullFinancialView
from gateway.pdf_input import extract_profile
from gateway.models import Scenario
from gateway.policy import domain_view
from gateway.inference import InferenceBroker,InferenceRequest,MODELS
from gateway.tax_evidence import expected_evidence
from scripts.run_ollama_bridge import validate_payload
runtime.ISOLATED=True
p,_=extract_profile([Path(f'dataset/Documents/C001_{k}.pdf').read_bytes() for k in ('mutuo','interessi')])
view=FullFinancialView.model_validate(full_view(p)) if runtime.UNMINIMIZED else TaxView.model_validate(domain_view(p,Scenario.TAX))
broker=InferenceBroker();sid=uuid4()
if runtime.UNMINIMIZED:broker._lab_profiles[sid]=view.model_dump(mode='json')
class Bridge:
 def revoke(self,owner):pass
 async def infer(self,payload,seconds,*,owner=None):
  assert validate_payload(payload)==payload
  assert payload['model']==MODELS['S-02']=='llama3.2:3b'
  assert payload['options']=={'num_ctx':4096,'num_predict':200,'temperature':0}
  assert 'think' not in payload
  data=json.loads(payload['messages'][1]['content'])
  assert data['context']==view.model_dump(mode='json')
  candidate={'schema_version':'tax-selection-1','source_statement_ids':['fixture_documents'],
    'context_statement_id':'context_tax_year','explanation':''}
  return {'body':{'message':{'content':json.dumps(candidate)},'prompt_eval_count':12,'eval_count':4,'load_duration':0},'ollama_ms':1}
broker.bridge=Bridge()
task=TaxTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view=view)
async def remote(t):
 evidence=expected_evidence(t.view)
 reply=await broker.infer(InferenceRequest(correlation_id=t.correlation_id,scenario='S-02',evidence=evidence.model_dump()),'Bearer '+t.inference_token)
 return TaxResult(correlation_id=t.correlation_id,status='completed',evidence=evidence,summary=reply.summary,
  limits=[],model=reply.model,tax_analysis=reply.tax_analysis)
async def main():
 result=await broker.delegate(sid,task,remote)
 assert result.tax_analysis['status']=='selection_only'
 assert result.measurements['gateway_analysis_receipt_verified']==1
 broker.revoke(sid)
 assert not broker._grants and not broker._lab_profiles and not broker._privacy
asyncio.run(main())
''',organization=organization,policy=policy)
    assert result.returncode==0,result.stderr
