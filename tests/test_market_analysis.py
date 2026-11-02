"""Selezione di enunciati controllati; nessuna inferenza o rete esterna."""
import json
from pathlib import Path

import pytest

from gateway.agent_contracts import MarketView
from gateway.ecb_source import EcbRateEvidence, parse_csv
from gateway.lab_profile import FullFinancialView, full_view
from gateway.market_analysis import (ANALYSIS_VERSION, build_analysis_input, check_analysis,
                                     market_schema, review_for_display, supported_numbers,
                                     validate_bridge_input)
from gateway.market_evidence import expected_evidence
from gateway.models import SessionInput


def view():
    return MarketView(mortgage_type='not_specified', rate_type='variable',
                      remaining_years_band={'lower_exclusive':20,'upper_inclusive':25})


def receipt():
    data=json.loads(Path('tests/fixtures/ecb_mir_public_response.json').read_text())
    row=parse_csv(data['source_csv'])
    return EcbRateEvidence(annual_rate_percent=row['OBS_VALUE'], observation_period=row['TIME_PERIOD'],
        source_csv=data['source_csv'], retrieved_at=data['retrieved_at'],response_sha256=data['response_sha256'])


def response(real=False,rate_type='variable'):
    return {'schema_version':ANALYSIS_VERSION,
            'source_statement_ids':['ecb_measure','ecb_not_profile_selected'] if real else ['fixture_nature','fixture_selection'],
            'context_statement_id':'context_rate_'+rate_type,
            'explanation':'Il riferimento offre un contesto generale rispetto al tipo di tasso indicato, senza descrivere il singolo contratto.'}


@pytest.mark.parametrize('real',[False,True])
def test_selected_texts_are_taken_from_catalog_without_semantic_certification(real):
    evidence=receipt() if real else expected_evidence(view())
    data=response(real)
    checked=check_analysis(json.dumps(data),view(),evidence)
    result=review_for_display(json.dumps(data),view(),evidence)
    catalog={s['statement_id']:s for s in build_analysis_input(view(),evidence)['statements']}
    assert checked.status=='statement_selection_checked'
    assert not checked.semantic_verified and not checked.approved_for_report
    assert result['status']=='available' and result['selected_statement_texts_checked']
    assert result['content']==data
    assert result['selected_statements']==[catalog[sid] for sid in [*data['source_statement_ids'],data['context_statement_id']]]
    assert not result['semantic_verified'] and not result['selection_relevance_verified']
    assert all(s['origin']!='verbatim_source_quote' for s in result['selected_statements'])


@pytest.mark.parametrize('real',[False,True])
@pytest.mark.parametrize('complete',[False,True])
def test_input_and_schema_preserve_mode_and_close_source_context_selections(real,complete):
    current=view()
    if complete:
        p=SessionInput.model_validate_json(Path('examples/session_complete.json').read_text()).profile
        current=FullFinancialView.model_validate(full_view(p))
    evidence=receipt() if real else expected_evidence(current)
    data=build_analysis_input(current,evidence)
    assert data['context']==current.model_dump(mode='json')
    assert data['evidence']['annual_rate_percent']==evidence.annual_rate_percent
    assert 'source_csv' not in data['evidence'] and 'response_sha256' not in data['evidence']
    assert validate_bridge_input(data,unminimized=complete)==data
    schema=market_schema(data)
    assert set(schema['properties'])=={'schema_version','source_statement_ids','context_statement_id','explanation'}
    assert set(schema['properties']['source_statement_ids']['items']['enum'])=={s['statement_id'] for s in data['statements'] if s['kind']=='source'}
    assert set(schema['properties']['context_statement_id']['enum'])=={s['statement_id'] for s in data['statements'] if s['kind']=='context'}
    if complete: assert 'context.financial_profile.remaining_principal.value' in data['reference_ids']


@pytest.mark.parametrize('fault',['unknown_source','other_source_catalog','unknown_context','wrong_context_kind',
                                  'duplicate','empty_selection','three_sources','new_field','wrong_type','old_contract'])
def test_invalid_selections_are_rejected_without_repair(fault):
    data=response()
    if fault=='unknown_source': data['source_statement_ids']=['unknown_source']
    if fault=='other_source_catalog':data['source_statement_ids']=['ecb_scope']
    if fault=='unknown_context':data['context_statement_id']='context_rate_fixed'
    if fault=='wrong_context_kind':data['context_statement_id']='fixture_nature'
    if fault=='duplicate':data['source_statement_ids']=['fixture_nature']*2
    if fault=='empty_selection':data['source_statement_ids']=[]
    if fault=='three_sources':data['source_statement_ids']=['fixture_nature','fixture_selection','source_period']
    if fault=='new_field':data['selected_statements']=[{'text':'Tasso personale garantito'}]
    if fault=='wrong_type':data['explanation']=123
    if fault=='old_contract':data={'schema_version':'market-context-1','relevance':{'text':'legacy'}}
    result=review_for_display(json.dumps(data),view(),expected_evidence(view()))
    assert result['status']=='rejected' and result['selected_statements']==[] and result['content'] is None
    assert not result['semantic_verified'] and result['issues']


@pytest.mark.parametrize('text',['', 'Conviene rinegoziare subito con un risparmio garantito.',
                                  'La durata è un fattore che determina i tassi.',
                                  'La fonte è un tasso annuo medio per tutti i nuovi mutui italiani.',
                                  'Il riferimento è pari a 999 euro ogni mese.',
                                  '<script>alert(1)</script>'])
def test_invalid_comment_keeps_real_model_selection_without_replacement(text):
    data=response();data['explanation']=text
    result=review_for_display(json.dumps(data),view(),expected_evidence(view()))
    assert result['status']=='selection_only' and result['issues']
    assert result['content']['source_statement_ids']==data['source_statement_ids']
    assert result['content']['explanation'] is None
    assert len(result['selected_statements'])==3
    assert text=='' or text not in json.dumps(result,ensure_ascii=False)


@pytest.mark.parametrize('raw',['','{}','Testo libero','```json\n{}\n```',
                               '{"schema_version":"market-selection-1","schema_version":"market-selection-1"}',
                               'x'*8193,None])
def test_absent_or_malformed_response_has_no_automatic_selection(raw):
    result=review_for_display(raw,view(),expected_evidence(view()))
    assert result['status']=='rejected' and not result['selected_statements']
    assert result['issues']==['invalid_model_response']


@pytest.mark.parametrize('fault',['altered_rate','missing_source','missing_receipt','expanded_view'])
def test_invalid_source_or_view_cannot_create_verified_statements(fault):
    evidence=expected_evidence(view()).model_dump();context=view().model_dump()
    if fault=='altered_rate':evidence['annual_rate_percent']='9.99'
    if fault=='missing_source':del evidence['source_id']
    if fault=='missing_receipt':evidence=receipt().model_dump(mode='json');del evidence['source_csv']
    if fault=='expanded_view':context['remaining_principal']='123456.78'
    result=review_for_display(json.dumps(response()),context,evidence)
    assert result['issues']==['invalid_input_evidence_or_view'] and result['source_sha256'] is None


@pytest.mark.parametrize('fault',['text','references','kind','id','extra'])
def test_bridge_regenerates_catalog_and_rejects_caller_supplied_statements(fault):
    data=build_analysis_input(view(),expected_evidence(view()))
    item=data['statements'][0]
    if fault=='text':item['text']='Una affermazione inventata dal chiamante.'
    if fault=='references':item['references']=['context.rate_type']
    if fault=='kind':item['kind']='context'
    if fault=='id':item['statement_id']='new_statement'
    if fault=='extra':data['statements'].append(dict(item))
    with pytest.raises(ValueError):validate_bridge_input(data)


def test_numbers_must_be_in_selected_statement_references_not_other_available_fields():
    data=response();data['explanation']='Il riferimento simulato è pari al 3.60 per cento annuo.'
    assert review_for_display(json.dumps(data),view(),expected_evidence(view()))['status']=='available'
    data['source_statement_ids']=['fixture_nature']
    assert review_for_display(json.dumps(data),view(),expected_evidence(view()))['status']=='selection_only'


@pytest.mark.parametrize('text,valid',[
    ('Il tasso citato è 3,60 per cento.',True),('Il tasso citato è 3.6 per cento.',True),
    ('Il tasso citato è -3.6 per cento.',False),('Il tasso citato è −3.6 per cento.',False),
    ('Il tasso citato è 3.6e3 per cento.',False),('Il periodo osservato è 2026-09.',True),
    ('Il periodo osservato è 2026-09-01.',False),('Il periodo osservato è 2025-09.',False),
    ('Il tasso citato è ³.⁶ per cento.',False)])
def test_numeric_values_sign_and_period_are_preserved(text,valid):
    refs={'evidence.annual_rate_percent':'3.60','evidence.observation_period':'2026-09'}
    assert supported_numbers(text,list(refs),refs) is valid


def test_numeric_suffix_of_identifier_does_not_authorize_an_amount():
    assert not supported_numbers('Il valore è 1.',['evidence.source_id'],{'evidence.source_id':'source-v1'})


def test_formal_acceptance_does_not_certify_arbitrary_semantic_claims():
    data=response();data['explanation']='Questa fonte descrive unicamente finanziamenti per automobili.'
    result=review_for_display(json.dumps(data),view(),expected_evidence(view()))
    assert not result['semantic_verified'] and not result['selection_relevance_verified']


@pytest.mark.parametrize('text,issue',[
    ('Il riferimento aiuta a descrivere il contesto del mutuo e di','possibly_incomplete_explanation'),
    ('Il contesto precisa anche la durata residua del mutuo.','unselected_statement_property'),
    ('Il mutuo della vista autorizzata è a tasso fisso.','unselected_statement_property')])
def test_observed_comment_problems_leave_valid_statements_available(text,issue):
    data=response();data['explanation']=text
    result=review_for_display(json.dumps(data),view(),expected_evidence(view()))
    assert result['status']=='selection_only' and issue in result['issues']
    assert result['selected_statements'] and result['content']['explanation'] is None


def test_comment_cannot_use_unselected_catalog_rule_even_if_rule_exists_in_prompt():
    data=response();data['source_statement_ids']=['fixture_nature']
    data['explanation']='Il valore viene scelto dalla tabella di test.'
    result=review_for_display(json.dumps(data),view(),expected_evidence(view()))
    assert result['status']=='selection_only' and 'unselected_statement_property' in result['issues']
