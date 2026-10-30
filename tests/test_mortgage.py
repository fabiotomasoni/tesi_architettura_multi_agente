from decimal import Decimal
from pathlib import Path
import pytest
from gateway.mortgage import payment,compare_mortgage
from gateway.pdf_input import extract_profile
from gateway.policy import make_view
from gateway.models import Scenario
from gateway.market_evidence import expected_evidence
from gateway.agent_contracts import MarketView


def profile(case='C001'):
    return extract_profile([Path('dataset/Documents',case+'_mutuo.pdf').read_bytes()])[0]


def activity(p):return {'status':'completed','result':{'evidence':expected_evidence(MarketView.model_validate(make_view(p,Scenario.MORTGAGE))).model_dump()}}


def test_zero_rate_and_one_period_closed_forms():
    assert payment(Decimal('1200'),12,Decimal('0'))==100
    assert abs(payment(Decimal('1000'),1,Decimal('12'))-Decimal('1010'))<Decimal('1e-40')


def test_independent_monthly_balance_recurrence():
    p=Decimal('100000');n=120;r=Decimal('3')
    installment=payment(p,n,r)
    balance=p
    for _ in range(n):balance=balance*(1+r/1200)-installment
    assert abs(balance)<Decimal('0.000001')


@pytest.mark.parametrize('case',['C001','C024'])
def test_dataset_matches_and_sign_is_transparent(case):
    p=profile(case);before=p.model_dump()
    result=compare_mortgage(p,activity(p))
    assert result['status']=='calculated'
    assert result['documented_vs_model']['matches_rounded_model']
    assert p.model_dump()==before
    assert result['personalized_recommendation'] is False
    if case=='C001':assert Decimal(result['difference_contract_minus_simulated']['monthly_payment'])<0
    else:
        assert Decimal(result['difference_contract_minus_simulated']['monthly_payment'])>0
        assert any('non previsioni' in x for x in result['limits'])


def test_missing_ambiguous_and_conflicts_block_calculations():
    for case in ['C006','C016']:
        p=profile(case)
        assert compare_mortgage(p,{'status':'blocked'})['status']=='not_calculated'
    p=profile()
    assert compare_mortgage(p,activity(p),has_conflicts=True)['reason']=='unresolved_conflict'


def test_no_evidence_or_nonmonthly_does_not_calculate():
    p=profile()
    assert compare_mortgage(p,{'status':'failed'})['status']=='not_calculated'
    p.payment_frequency.value='quarterly'
    assert compare_mortgage(p,activity(p))['reason']=='unsupported_payment_frequency'


def test_document_payment_difference_not_silently_corrected():
    p=profile();p.payment_amount.value='1.00'
    result=compare_mortgage(p,activity(p))
    assert not result['documented_vs_model']['matches_rounded_model']
    assert result['documented_monthly_payment']=='1.00'
    assert p.payment_amount.value=='1.00'


@pytest.mark.parametrize('principal,n,rate',[('0',12,'3'),('10',0,'3'),('10',12,'NaN'),('-1',12,'3')])
def test_invalid_parameters(principal,n,rate):
    with pytest.raises(ValueError):payment(Decimal(principal),n,Decimal(rate))


def test_independent_report_checker():
    from scripts.check_mortgage import verify
    from gateway.report import build_report
    p=profile('C024')
    a=activity(p);a['result'].update(summary='demo',model='test',limits=[])
    report=build_report(p,['S-01'],{'S-01':a},'completed')
    assert all(verify(report).values())
    report['mortgage_comparison']['simulated_rate_scenario']['theoretical_monthly_payment']='1.00'
    assert not all(verify(report).values())
