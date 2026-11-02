"""Gateway e report con risposta modello controllata; nessuna inferenza reale."""
import asyncio
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from gateway.agent_contracts import MarketTask,MarketResult,MarketView
from gateway.a2a_egress import EgressDenied
from gateway.inference import InferenceBroker,InferenceRequest,MODELS,OLLAMA_ENDPOINT
from gateway.market_analysis import (ANALYSIS_VERSION,build_analysis_input,market_payload,
                                     review_for_display,MARKET_ANALYSIS_PROMPT)
from gateway.market_evidence import expected_evidence
from gateway.models import SessionInput,Scenario
from gateway.policy import domain_view
from gateway.report import build_report
from gateway.report_document import render_report_document
from scripts.run_ollama_bridge import validate_payload


def candidate():
    return {'schema_version':ANALYSIS_VERSION,'source_statement_ids':['fixture_nature','fixture_selection'],
            'context_statement_id':'context_rate_fixed',
            'explanation':'Il riferimento ipotetico dipende dal tipo di tasso ricevuto, senza attestare le condizioni del contratto individuale.'}


def profile():
    return SessionInput.model_validate_json(Path('examples/session_complete.json').read_text()).profile


def roundtrip(monkeypatch,response,*,forged=None,unavailable=False):
    p=profile();view=MarketView.model_validate(domain_view(p,Scenario.MORTGAGE));evidence=expected_evidence(view)
    task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view=view)
    broker=InferenceBroker();sent=[];original=httpx.AsyncClient
    def receive(request):
        assert str(request.url)==OLLAMA_ENDPOINT
        payload=json.loads(request.content);assert validate_payload(payload)==payload;sent.append(payload)
        if unavailable:return httpx.Response(503)
        return httpx.Response(200,json={'message':{'content':response},'prompt_eval_count':120,'eval_count':90,'load_duration':1000000})
    async def remote(authorized):
        inferred=await broker.infer(InferenceRequest(correlation_id=authorized.correlation_id,scenario='S-01',evidence=evidence.model_dump(mode='json')),'Bearer '+authorized.inference_token)
        analysis=deepcopy(inferred.market_analysis)
        if forged=='comment':analysis['content']['explanation']='Testo sostituito dopo la risposta del modello.'
        if forged=='statement_text':analysis['selected_statements'][0]['text']='Un fatto completamente inventato.'
        if forged=='selection_ids':analysis['content']['source_statement_ids']=['fixture_not_contract']
        if forged=='drop':analysis=None
        return MarketResult(correlation_id=authorized.correlation_id,status='completed',evidence=evidence,
            summary=inferred.summary,model='unconfigured-model' if forged=='model' else inferred.model,
            limits=[],market_analysis=analysis)
    with monkeypatch.context() as patch:
        patch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
        try:result=asyncio.run(broker.delegate(uuid4(),task,remote))
        finally:assert not broker._grants and not broker._privacy
    activities={'S-01':{'status':'completed','error_code':None,'result':result.model_dump(mode='json')}}
    return build_report(p,['S-01'],activities,'completed'),result,sent


def test_model_selection_and_separate_comment_reach_json_and_html(monkeypatch):
    report,result,sent=roundtrip(monkeypatch,json.dumps(candidate()))
    generated=report['model_analyses'][0]
    assert generated['status']=='available' and not generated['semantic_verified']
    assert not generated['selection_relevance_verified']
    assert generated['content']==candidate()
    assert generated['gateway_model_output_receipt_verified']
    assert result.measurements['gateway_analysis_receipt_verified']==1
    assert len(generated['selected_statements'])==3
    assert generated['references']['context.rate_type']==profile().rate_type.value
    assert sent[0]['messages'][0]['content']==MARKET_ANALYSIS_PROMPT
    assert sent[0]['options']['num_predict']==768 and len(sent)==1
    html=render_report_document(report)
    assert candidate()['explanation'] in html
    assert all(item['text'] in html for item in generated['selected_statements'])
    assert 'non sono citazioni letterali' in html and 'non verificate semanticamente' in html
    assert report['model_evaluation'][0]['selection_included'] and report['model_evaluation'][0]['free_text_included']


def test_real_selection_changes_report_focus_without_changing_financial_facts(monkeypatch):
    first,_,_=roundtrip(monkeypatch,json.dumps(candidate()))
    other=candidate();other['source_statement_ids']=['fixture_not_contract']
    other['explanation']='Il riferimento ipotetico non attesta il tasso applicato al contratto ricevuto.'
    second,_,_=roundtrip(monkeypatch,json.dumps(other))
    assert first['model_analyses'][0]['selected_statements']!=second['model_analyses'][0]['selected_statements']
    assert first['model_analyses'][0]['output_sha256']!=second['model_analyses'][0]['output_sha256']
    for key in ('document_data','faithful_summaries','mortgage_contract_analysis','mortgage_comparison'):
        assert first[key]==second[key]


@pytest.mark.parametrize('text',['','Il beneficio è pari a 999 euro al mese.',
                                'Conviene rinegoziare immediatamente con risparmio garantito.',
                                'La durata è un fattore importante per determinare il tasso.',
                                'La fonte descrive un tasso annuo medio per tutti i mutui simulati.'])
def test_comment_failure_does_not_erase_verified_model_selection(monkeypatch,text):
    data=candidate();data['explanation']=text
    report,_,_=roundtrip(monkeypatch,json.dumps(data))
    generated=report['model_analyses'][0]
    assert generated['status']=='selection_only' and generated['content']['explanation'] is None
    assert len(generated['selected_statements'])==3
    html=render_report_document(report)
    assert 'Commento escluso' in html
    assert text=='' or text not in html
    assert all(item['text'] in html for item in generated['selected_statements'])
    assert report['mortgage_contract_analysis']['status']=='calculated'
    assert report['model_evaluation'][0]['selection_included'] and not report['model_evaluation'][0]['free_text_included']


@pytest.mark.parametrize('raw',['','Una risposta non strutturata.',json.dumps({**candidate(),'source_statement_ids':['invented_statement']})])
def test_missing_or_invalid_selection_does_not_produce_a_fallback(monkeypatch,raw):
    report,_,_=roundtrip(monkeypatch,raw)
    generated=report['model_analyses'][0]
    assert generated['status']=='rejected' and not generated['selected_statements']
    assert report['simulated_sources'] and report['mortgage_contract_analysis']['status']=='calculated'
    assert not report['model_evaluation'][0]['selection_included']


@pytest.mark.parametrize('forged',['comment','statement_text','selection_ids','drop','model'])
def test_agent_cannot_replace_model_choices_text_or_identity(monkeypatch,forged):
    with pytest.raises(EgressDenied):roundtrip(monkeypatch,json.dumps(candidate()),forged=forged)


def test_model_unavailable_has_no_selection_or_fabricated_interpretation(monkeypatch):
    with pytest.raises(httpx.HTTPStatusError):roundtrip(monkeypatch,'',unavailable=True)


def test_report_requires_gateway_receipt_and_regenerates_catalog_texts():
    p=profile();view=MarketView.model_validate(domain_view(p,Scenario.MORTGAGE));evidence=expected_evidence(view)
    reviewed=review_for_display(json.dumps(candidate()),view,evidence)
    reviewed['selected_statements'][0]['text']='Una frase inventata dal chiamante.'
    result={'evidence':evidence.model_dump(),'summary':'test','model':'controlled','market_analysis':reviewed}
    activity={'S-01':{'status':'completed','result':result}}
    assert build_report(p,['S-01'],activity,'completed')['model_analyses'][0]['status']=='unavailable'
    result['measurements']={'gateway_analysis_receipt_verified':1}
    report=build_report(p,['S-01'],activity,'completed')
    assert report['model_analyses'][0]['status']=='available'
    assert 'Una frase inventata' not in render_report_document(report)


@pytest.mark.parametrize('fault',['format','prompt','prompt_suffix','reference_ids','raw_pdf','expanded_context','options','statement'])
def test_bridge_rejects_changed_payload_or_source_statement(fault):
    view=MarketView.model_validate(domain_view(profile(),Scenario.MORTGAGE))
    payload=market_payload(MODELS['S-01'],build_analysis_input(view,expected_evidence(view)))
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
