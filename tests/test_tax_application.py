from pathlib import Path
from decimal import Decimal
import pytest
from gateway.pdf_input import extract_profile
from gateway.tax_application import apply_tax_scenario
from gateway.tax_evidence import expected_evidence
from gateway.agent_contracts import TaxView


def profile(case):return extract_profile([Path('dataset/Documents',case+'_interessi.pdf').read_bytes()])[0]

def activity(p):return {'status':'completed','result':{'evidence':expected_evidence(TaxView(tax_year=int(str(p.tax_year.value)),purpose=p.purpose.value)).model_dump()}}


@pytest.mark.parametrize('case',['C001','C004','C024'])
def test_product_independent_integer_arithmetic_and_no_entitlement(case):
    p=profile(case);before=p.model_dump()
    result=apply_tax_scenario(p,activity(p))
    cents=int(Decimal(str(p.annual_interest.value))*100)
    percent=int(Decimal(str(p.ownership_share.value))*100)
    expected_cents=(cents*percent+50)//100
    assert Decimal(result['hypothetical_allocation']['amount_EUR'])*100==expected_cents
    assert result['deduction_calculated'] is False
    assert result['tax_entitlement']=='not_assessed'
    assert result['hypothetical_allocation']['documented_as_personal_amount'] is False
    assert p.model_dump()==before


def test_half_cent_rounding_and_zero_interest():
    p=profile('C004');p.annual_interest.value='0.01';p.ownership_share.value='0.5'
    assert apply_tax_scenario(p,activity(p))['hypothetical_allocation']['amount_EUR']=='0.01'
    p.annual_interest.value='0'
    assert apply_tax_scenario(p,activity(p))['hypothetical_allocation']['amount_EUR']=='0.00'


def test_missing_unvalidated_bad_period_bad_share_and_conflict():
    p=profile('C011')
    assert apply_tax_scenario(p,activity(p))['reason']=='input_not_ready'
    for mutation in ['ambiguous','period','share']:
        p=profile('C001')
        if mutation=='ambiguous':p.annual_interest.status='ambiguous'
        elif mutation=='period':p.tax_year.value='2024'
        else:p.ownership_share.value='1.1'
        assert apply_tax_scenario(p,activity(p))['status']=='not_calculated'
    p=profile('C001')
    assert apply_tax_scenario(p,activity(p),has_conflicts=True)['reason']=='unresolved_conflict'
    assert apply_tax_scenario(p,{'status':'failed'})['reason']=='tax_evidence_unavailable'


def test_source_alteration_rejected_and_assumption_explicit():
    p=profile('C001');a=activity(p)
    a['result']['evidence']['conditions']=['La detrazione spetta.']
    with pytest.raises(ValueError):apply_tax_scenario(p,a)
    result=apply_tax_scenario(p,activity(p))
    assert any('non già ripartiti' in text for text in result['assumptions'])
    assert any('doppia ripartizione' in text for text in result['limits'])


def test_report_and_rational_verifier_detect_tampering():
    from gateway.report import build_report
    from scripts.check_tax_application import verify
    p=profile('C024');a=activity(p);a['result'].update(summary='demo',model='test',limits=[])
    report=build_report(p,['S-02'],{'S-02':a},'completed')
    assert report['mortgage_comparison'] is None
    assert all(verify(report).values())
    report['tax_application']['hypothetical_allocation']['amount_EUR']='1.00'
    assert not all(verify(report).values())
