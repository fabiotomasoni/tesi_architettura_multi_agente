from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import pytest
from gateway.mortgage import analyze_contract
from gateway.report import build_report
from gateway.report_document import render_report_document
from scripts.check_mortgage import verify
from tests.test_mortgage import profile,activity


@pytest.mark.parametrize('case',['C001','C024'])
@pytest.mark.parametrize('remote',['fixture','failed','unverified','blocked','ecb'])
def test_contract_survives_source_limit_or_failure(case,remote):
    p=profile(case);before=p.model_dump()
    a=activity(p)
    if remote=='ecb':
        from tests.test_ecb_source import evidence
        a['result']['evidence']=evidence().model_dump(mode='json')
        a['result']['measurements']={'gateway_source_receipt_verified':1}
    elif remote!='fixture':a={'status':remote,'error_code':'timeout' if remote=='failed' else 'not_authorized' if remote=='blocked' else 'missing_provenance','result':None}
    if a.get('result'):a['result'].update(summary='Non usare',model='test')
    r=build_report(p,['S-01'],{'S-01':a},'completed' if remote in {'fixture','ecb'} else remote)
    assert r['mortgage_contract_analysis']['status']=='calculated'
    assert all(verify(r).values())
    assert p.model_dump()==before
    if remote!='fixture':
        assert r['mortgage_comparison']['status']=='not_calculated'
        assert 'simulated_rate_scenario' not in r['mortgage_comparison']
    html=render_report_document(r)
    assert 'Rata mensile teorica' in html and 'Scostamento rata documentata' in html
    assert 'non previsione' in html if case=='C024' else True


@pytest.mark.parametrize('fault',['missing','ambiguous','period','unit','conflict','frequency','duration'])
def test_local_invalid_data_fail_closed(fault):
    p=profile('C006' if fault=='missing' else 'C016' if fault=='ambiguous' else 'C001')
    if fault=='period':p.annual_rate.period+=timedelta(days=1)
    if fault=='unit':p.remaining_principal.unit='USD'
    if fault=='frequency':p.payment_frequency.value='quarterly'
    if fault=='duration':p.remaining_months.value='1201'
    r=analyze_contract(p,has_conflicts=fault=='conflict')
    assert r['status']=='not_calculated' and r['assumptions']==[]
    assert 'contract_rate_scenario' not in r


def test_document_payment_is_preserved_and_checker_rejects_corruption():
    p=profile();p.payment_amount.value='1.00'
    a=activity(p);a['result'].update(summary='test',model='test')
    r=build_report(p,['S-01'],{'S-01':a},'completed')
    c=r['mortgage_contract_analysis']
    assert c['documented_monthly_payment']=='1.00' and not c['documented_vs_model']['matches_rounded_model']
    assert all(verify(r).values())
    for field in ['theoretical_monthly_payment','theoretical_total_interest','annual_rate_percent']:
        wrong=deepcopy(r);wrong['mortgage_contract_analysis']['contract_rate_scenario'][field]='0'
        assert not all(verify(wrong).values())


def test_tax_only_has_no_contract_analysis():
    from gateway.pdf_input import extract_profile
    from pathlib import Path
    p,_=extract_profile([Path('dataset/Documents/C001_interessi.pdf').read_bytes()])
    r=build_report(p,['S-02'],{'S-02':{'status':'failed','error_code':'timeout'}},'failed')
    assert r['mortgage_contract_analysis'] is None
    assert 'Analisi locale del contratto' not in render_report_document(r)


def test_direct_cli_for_new_local_analysis(tmp_path):
    import json,subprocess,sys
    p=profile();a={'status':'failed','error_code':'timeout'}
    r=build_report(p,['S-01'],{'S-01':a},'failed')
    path=tmp_path/'report.json';path.write_text(json.dumps(r))
    result=subprocess.run([sys.executable,'scripts/check_mortgage.py',str(path)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'contract_monthly_payment: True' in result.stdout
    r['mortgage_contract_analysis']['contract_rate_scenario']['theoretical_monthly_payment']='0'
    path.write_text(json.dumps(r))
    result=subprocess.run([sys.executable,'scripts/check_mortgage.py',str(path)],capture_output=True,text=True)
    assert result.returncode==1


@pytest.mark.parametrize('tampering',['period','status','unit'])
def test_report_builder_does_not_calculate_invalid_contract(tampering):
    p=profile()
    if tampering=='period':p.annual_rate.period+=timedelta(days=1)
    elif tampering=='status':p.remaining_principal.status='ambiguous'
    else:p.annual_rate.unit='EUR'
    a={'status':'blocked','error_code':'input_not_ready'}
    r=build_report(p,['S-01'],{'S-01':a},'blocked')
    assert r['mortgage_contract_analysis']['status']=='not_calculated'
    assert all(verify(r).values())
    assert 'Rata mensile teorica' not in render_report_document(r)
