from copy import deepcopy
from pathlib import Path
from decimal import Decimal
import csv,json,subprocess,sys
import pytest
from scripts.evaluation_support import utility,quality_score
from scripts.check_evaluation_protocol import verify,annotation_checks,review_checks
ROOT=Path(__file__).resolve().parents[1]


def reference():return json.loads((ROOT/'evaluation/annotations.json').read_text())


def test_protocol_is_draft_and_reference_matches_fixed_pdfs():
    protocol=json.loads((ROOT/'evaluation/protocol.json').read_text())
    assert all(verify(protocol,reference()).values())
    assert protocol['approved_by'] is None and protocol['evaluators']['count']==1


def test_missing_and_ambiguous_latent_values_are_not_expected_answers():
    cases={c['case_id']:c for c in reference()['cases']}
    assert cases['C006']['facts']['remaining_principal']['value'] is None
    assert cases['C011']['facts']['annual_interest']['value'] is None
    assert cases['C016']['facts']['annual_rate']['value'] is None
    assert 'contract' not in cases['C006']['expected_calculations']
    assert 'hypothetical_interest_share' not in cases['C011']['expected_calculations']
    assert cases['C016']['agent_utility_facts']['S-01'] is None


def test_annotations_do_not_contain_direct_identifiers_or_runtime_outputs():
    encoded=json.dumps(reference())
    for key in ['person','cf','iban','address','email','employer','movements','agent_boot_id','inference_token']:
        assert '"'+key+'"' not in encoded
    assert 'Marco Riva' not in encoded and 'example.invalid' not in encoded
    assert not (ROOT/'gateway/evaluation').exists()


def test_utility_keeps_local_values_out_of_agent_denominator():
    c=reference()['cases'][0];facts=c['agent_utility_facts']['S-01']
    minimal={'rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10},'mortgage_type':'not_specified'}
    assert utility(minimal,facts)['ratio']==1
    excessive={**minimal,'rate_type':'any'}
    score=utility(excessive,facts);assert score['ratio']==.5 and score['unusable_fields']==['rate_type']
    assert score['ratio']<.95
    assert utility({},None)['ratio'] is None


def test_more_precise_view_preserves_required_granularity_without_rewarding_extras():
    c=reference()['cases'][0]
    full={'financial_profile':{k:{p:v for p,v in f.items() if p in {'value','unit','period','status'}} for k,f in c['facts'].items() if f['status']=='validated'}}
    for s in ('S-01','S-02'):assert utility(full,c['agent_utility_facts'][s])['ratio']==1
    changed=deepcopy(full);changed['financial_profile']['remaining_months']['value']='121'
    assert utility(changed,c['agent_utility_facts']['S-01'])['ratio']==.5
    changed=deepcopy(full);changed['financial_profile']['tax_year']['status']='ambiguous'
    assert utility(changed,c['agent_utility_facts']['S-02'])['ratio']==.5


@pytest.mark.parametrize('row',[
 {},{'correctness':'','coverage':'2','provenance':'2','limits':'2','critical_error':'no'},
 {'correctness':'3','coverage':'2','provenance':'2','limits':'2','critical_error':'no'},
 {'correctness':'2','coverage':'2','provenance':'2','limits':'2','critical_error':'yes','notes':''}])
def test_human_scores_are_never_filled_or_inferred(row):
    with pytest.raises(ValueError):quality_score(row)


def test_critical_error_cannot_be_compensated_by_good_scores():
    row={'correctness':'2','coverage':'2','provenance':'2','limits':'2','critical_error':'yes','notes':'Conclusione fiscale non supportata'}
    assert not quality_score(row)['meets_individual_thresholds']
    row['critical_error']='no';assert quality_score(row)['total']==8


def test_reference_numbers_are_checked_against_documents_not_parser_output():
    modified=reference();modified['cases'][0]['facts']['remaining_principal']['value']='1'
    assert not all(annotation_checks(modified,ROOT/'dataset/Documents').values())
    modified=reference();modified['cases'][5]['facts']['remaining_principal']['value']='123'
    assert not all(annotation_checks(modified,ROOT/'dataset/Documents').values())


def test_cli_audit_does_not_authorize_final_campaign():
    ok=subprocess.run([sys.executable,'scripts/check_evaluation_protocol.py'],cwd=ROOT,capture_output=True,text=True)
    assert ok.returncode==0,ok.stdout+ok.stderr
    assert 'Campagna finale autorizzata: False' in ok.stdout
    frozen=subprocess.run([sys.executable,'scripts/check_evaluation_protocol.py','--require-frozen'],cwd=ROOT,capture_output=True,text=True)
    assert frozen.returncode!=0
    assert 'Nessuna campagna avviata' in frozen.stderr


@pytest.mark.parametrize('field,value',[('period','2020-01-01'),('unit','USD')])
def test_reference_periods_and_units_are_checked(field,value):
    modified=reference();modified['cases'][0]['facts']['remaining_principal'][field]=value
    assert not all(annotation_checks(modified,ROOT/'dataset/Documents').values())


def test_independent_reference_calculation_and_non_forecast_limit():
    cases={c['case_id']:c for c in reference()['cases']}
    assert cases['C001']['expected_calculations']['contract']['monthly_payment']=='1604.32'
    assert cases['C001']['expected_calculations']['contract']['remaining_interest']=='7429.08'
    assert 'variable_or_mixed_frozen_rate_not_forecast' in cases['C024']['required_report_limits']


def test_threshold_approval_does_not_approve_annotations_or_campaign():
    p=json.loads((ROOT/'evaluation/protocol.json').read_text())
    assert p['threshold_approval']['status']=='approved'
    assert p['frozen_at'] is None and p['approved_by'] is None
    assert p['freeze_blockers']  # Restano altre verifiche anche con annotazioni confermate.
    assert p['security_stage']=='S04_not_authorized' and not p['final_campaign_started']
    altered=deepcopy(p);altered['thresholds']['human_quality']['minimum_per_report']=0
    assert not all(verify(altered,reference()).values())


def test_only_explicitly_confirmed_cases_are_recorded_without_human_report_scores():
    protocol=json.loads((ROOT/'evaluation/protocol.json').read_text())
    review=protocol['annotation_review']
    assert set(review['confirmed_cases'])=={f'C{i:03}' for i in range(1,26)}
    assert all(review_checks(review,reference()).values())
    assert reference()['status']=='human_reviewed' and review['status']=='complete'
    assert 'human_review_of_annotations' not in protocol['freeze_blockers']
    assert protocol['status']=='draft_pending_verification'
    assert not protocol['final_campaign_started'] and protocol['approved_by'] is None
    with (ROOT/'evaluation/human_review_template.csv').open() as stream:
        assert list(csv.DictReader(stream))==[]


def test_confirmation_is_invalidated_by_change_to_the_reviewed_case_but_not_other_cases():
    # Una registrazione parziale resta valida se cambia un caso non ancora rivisto.
    review=deepcopy(json.loads((ROOT/'evaluation/protocol.json').read_text())['annotation_review'])
    review['status']='partial';review['confirmed_cases']={k:v for k,v in review['confirmed_cases'].items() if k in {'C001','C006','C011','C016','C021'}}
    draft=reference();draft['status']='draft_pending_human_review'
    changed=deepcopy(draft);changed['cases'][0]['facts']['remaining_principal']['value']='1'
    assert not all(review_checks(review,changed).values())
    changed=deepcopy(draft);changed['cases'][1]['facts']['remaining_principal']['value']='1'
    assert all(review_checks(review,changed).values())
    changed=deepcopy(review);changed['confirmed_cases']['C999']='0'*64
    assert not all(review_checks(changed,draft).values())


def test_complete_review_cannot_omit_a_case_or_keep_pending_annotation_status():
    protocol=json.loads((ROOT/'evaluation/protocol.json').read_text())
    review=deepcopy(protocol['annotation_review']);review['confirmed_cases'].pop('C025')
    assert not all(review_checks(review,reference()).values())
    changed=reference();changed['status']='draft_pending_human_review'
    assert not all(review_checks(protocol['annotation_review'],changed).values())
    changed=reference();changed['cases'][24]['facts']['annual_interest']['value']='1'
    assert not all(review_checks(protocol['annotation_review'],changed).values())


def test_annotation_confirmation_does_not_remove_other_campaign_gates():
    protocol=json.loads((ROOT/'evaluation/protocol.json').read_text())
    assert 'approve_remaining_S04_scope' in protocol['freeze_blockers']
    assert protocol['security_stage']=='S04_not_authorized'
    changed=deepcopy(protocol);changed['freeze_blockers'].append('human_review_of_annotations')
    assert not all(verify(changed,reference()).values())
