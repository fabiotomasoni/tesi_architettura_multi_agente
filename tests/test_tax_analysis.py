"""Fedeltà del catalogo fiscale: due edizioni, finalità e viste autorizzate."""
import json
from datetime import datetime,timezone
from pathlib import Path

import pytest

from gateway.ade_source import AdeEvidence,publication,selected_quotes
from gateway.agent_contracts import TaxView
from gateway.lab_profile import FullFinancialView,full_view
from gateway.models import SessionInput
from gateway.tax_analysis import (ANALYSIS_VERSION,build_analysis_input,review_for_display,
                                  validate_bridge_input,tax_payload)
from gateway.tax_evidence import expected_evidence
from gateway.tax_review import RULE_GROUPS
from gateway.tax_review_rules import RULES

PURPOSES=('primary_home_purchase','primary_home_construction','renovation','other')


def real_evidence(year=2025,purpose='primary_home_purchase'):
    p=publication(year)
    return AdeEvidence(**(p|{'purpose':purpose,'quotes':selected_quotes(year,purpose),
                             'retrieved_at':datetime.now(timezone.utc)}))


def candidate(real=False):
    return {'schema_version':ANALYSIS_VERSION,
            'source_statement_ids':['paid_year','own_share'] if real else ['fixture_documents','fixture_personal_requirements'],
            'context_statement_id':'context_purpose',
            'explanation':'Le condizioni evidenziate vanno approfondite in relazione alla finalità dichiarata nella vista.'}


@pytest.mark.parametrize('year',[2024,2025])
@pytest.mark.parametrize('purpose',PURPOSES)
def test_selected_conditions_keep_exact_edition_quotes_and_unassessed_personal_state(year,purpose):
    view=TaxView(tax_year=year,purpose=purpose);evidence=real_evidence(year,purpose)
    result=review_for_display(json.dumps(candidate(True)),view,evidence)
    assert result['status']=='available' and result['selected_statement_texts_checked']
    assert not result['semantic_verified'] and not result['selection_relevance_verified']
    assert result['tax_entitlement']=='not_assessed' and not result['deduction_calculated']
    assert not result['personalized_recommendation']
    for item in result['selected_statements']:
        if item['kind']!='source':continue
        rule=RULES[str(year)][item['statement_id']];source=item['source']
        assert item['text']==rule['question'] and item['needed_information']==rule['needed_information']
        assert source['quote']==rule['quote'] and source['page']==rule['page']
        assert source['document_sha256']==publication(year)['document_sha256']
        assert source['tax_year']==year and source['publication_year']==year+1
        assert source['source_ref']==source['source_url']+'#page='+str(rule['page'])
        assert item['status']=='to_verify' and item['personal_verification']=='not_assessed'
        assert item['applicability']=='candidate_only'


@pytest.mark.parametrize('real',[False,True])
@pytest.mark.parametrize('complete',[False,True])
@pytest.mark.parametrize('purpose',PURPOSES)
def test_packet_retains_full_lab_profile_or_only_tax_minimum_and_bridge_rebuilds_it(real,complete,purpose):
    view=TaxView(tax_year=2025,purpose=purpose)
    if complete:
        profile=SessionInput.model_validate_json(Path('examples/session_complete.json').read_text()).profile
        profile.purpose.value=purpose
        view=FullFinancialView.model_validate(full_view(profile))
    evidence=real_evidence(view.tax_year,view.purpose) if real else expected_evidence(view)
    data=build_analysis_input(view,evidence)
    assert data['context']==view.model_dump(mode='json')
    assert validate_bridge_input(data,unminimized=complete)==data
    expected=set(RULE_GROUPS[purpose]) if real else {'fixture_documents','fixture_personal_requirements','fixture_no_entitlement'}
    assert {s['statement_id'] for s in data['statements'] if s['kind']=='source'}==expected
    if not complete:
        assert set(data['context'])=={'tax_year','expense_category','purpose'}
        assert not any(field in json.dumps(data) for field in ('annual_interest','ownership_share','financial_profile'))
    else:
        assert 'annual_interest' in data['context']['financial_profile']
    payload=tax_payload('qwen3:1.7b',data)
    assert payload['think'] is False and payload['options']=={'num_ctx':4096,'num_predict':200,'temperature':0}


@pytest.mark.parametrize('fault',['unknown','wrong_year_group','wrong_purpose_group','market_id','duplicate','wrong_context','extra_field','empty','old_contract'])
def test_unknown_or_inconsistent_choices_are_not_repaired(fault):
    view=TaxView(tax_year=2025,purpose='primary_home_purchase');data=candidate(True)
    if fault=='unknown':data['source_statement_ids']=['invented_condition']
    if fault=='wrong_year_group':data['source_statement_ids']=['condition_2024']
    if fault=='wrong_purpose_group':data['source_statement_ids']=['renovation_1997']
    if fault=='market_id':data['source_statement_ids']=['ecb_measure']
    if fault=='duplicate':data['source_statement_ids']=['paid_year','paid_year']
    if fault=='wrong_context':data['context_statement_id']='paid_year'
    if fault=='extra_field':data['tax_entitlement']='eligible'
    if fault=='empty':data['source_statement_ids']=[]
    if fault=='old_contract':data={'summary':'Un testo del vecchio percorso'}
    result=review_for_display(json.dumps(data),view,real_evidence())
    assert result['status']=='rejected' and not result['selected_statements'] and result['content'] is None


@pytest.mark.parametrize('text',['','Ti spetta la detrazione richiesta.', 'La detrazione non è garantita.',
                                'Puoi applicare una aliquota del 19%.', 'Il valore disponibile è 999 euro.',
                                'Le condizioni vanno approfondite in relazione al', '<script>azione()</script>'])
def test_comment_is_optional_and_cannot_promote_personal_entitlement(text):
    data=candidate(True);data['explanation']=text
    result=review_for_display(json.dumps(data),TaxView(tax_year=2025,purpose='primary_home_purchase'),real_evidence())
    assert result['status']=='selection_only' and result['content']['explanation'] is None
    assert len(result['selected_statements'])==3
    assert not result['deduction_calculated'] and result['tax_entitlement']=='not_assessed'
    assert text=='' or text not in json.dumps(result,ensure_ascii=False)


@pytest.mark.parametrize('fault',['quote','page','publication_year','tax_year','context','statement','reference'])
def test_bridge_rejects_changed_projection_or_catalog(fault):
    view=TaxView(tax_year=2025,purpose='primary_home_purchase')
    data=build_analysis_input(view,real_evidence())
    if fault=='quote':data['evidence']['rule_quotes']['paid_year']['text']='Una citazione inventata.'
    if fault=='page':data['evidence']['rule_quotes']['paid_year']['page']=1
    if fault=='publication_year':data['evidence']['publication_year']=2025
    if fault=='tax_year':data['evidence']['tax_year']=2024
    if fault=='context':data['context']['annual_interest']='1000.00'
    if fault=='statement':data['statements'][0]['text']='Un requisito personale già soddisfatto.'
    if fault=='reference':data['reference_ids'].append('context.annual_interest')
    with pytest.raises(ValueError):validate_bridge_input(data)


@pytest.mark.parametrize('fault',['quote','digest','year','purpose','receipt','simulated_changed'])
def test_source_must_be_verified_before_preparing_candidates(fault):
    view=TaxView(tax_year=2025,purpose='primary_home_purchase');evidence=real_evidence().model_dump(mode='json')
    if fault=='quote':evidence['quotes'][0]['text']='Un estratto inventato.'
    if fault=='digest':evidence['document_sha256']='0'*64
    if fault=='year':evidence['tax_year']=2024
    if fault=='purpose':evidence['purpose']='renovation'
    if fault=='receipt':del evidence['retrieved_at']
    if fault=='simulated_changed':evidence['simulated']=True
    result=review_for_display(json.dumps(candidate(True)),view,evidence)
    assert result['issues']==['invalid_input_evidence_or_view'] and not result['selected_statements']


@pytest.mark.parametrize('raw',['',None,'Non ho una risposta','{}','```json\n{}\n```','x'*8193,
                               '{"schema_version":"tax-selection-1","schema_version":"tax-selection-1"}'])
def test_malformed_model_output_does_not_invent_conditions(raw):
    view=TaxView(tax_year=2025,purpose='other')
    result=review_for_display(raw,view,expected_evidence(view))
    assert result['status']=='rejected' and result['issues']==['invalid_model_selection']


def test_fixture_choices_remain_simulated_and_never_get_official_quotes():
    view=TaxView(tax_year=2024,purpose='renovation')
    result=review_for_display(json.dumps(candidate()),view,expected_evidence(view))
    assert result['source_kind']=='simulated'
    assert all(s['source']['simulated'] is True for s in result['selected_statements'] if s['kind']=='source')
    assert not any('document_sha256' in (s.get('source') or {}) for s in result['selected_statements'])


@pytest.mark.parametrize('text', ["L’anno indicato nella vista corrisponde al mutu", "Le informazioni riguardano la ristruttur-", "La condizione resta da verificare"])
def test_incomplete_model_sentences_are_excluded(text):
    view=TaxView(tax_year=2025,purpose='primary_home_purchase')
    data={'schema_version':ANALYSIS_VERSION,'source_statement_ids':['fixture_documents'],
          'context_statement_id':'context_tax_year','explanation':text}
    result=review_for_display(json.dumps(data),view,expected_evidence(view))
    assert result['status']=='selection_only'
    assert 'possibly_incomplete_explanation' in result['issues']
    assert result['content']['explanation'] is None
