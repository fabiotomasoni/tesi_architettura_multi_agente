from copy import deepcopy
import json,subprocess,sys
from pathlib import Path
import pytest
from gateway.pdf_input import extract_profile
from gateway.report import build_report
from gateway.report_document import render_report_document
from gateway.tax_review import build_tax_review
from scripts.check_tax_review import verify
from tests.test_ade_source import evidence


def profile(case):return extract_profile([Path(f'dataset/Documents/{case}_interessi.pdf').read_bytes()])[0]


def report(case='C001',purpose=None):
    p=profile(case)
    if purpose:p.purpose.value=purpose
    a={'status':'completed','result':{'model':'test','summary':'Sicuramente ti spetta una detrazione','evidence':evidence(int(str(p.tax_year.value)),p.purpose.value).model_dump(mode='json'),'measurements':{'gateway_source_receipt_verified':1}}}
    return build_report(p,['S-02'],{'S-02':a},'completed')


@pytest.mark.parametrize('case',['C001','C006','C021','C022'])
def test_annual_purpose_conditions_and_facts(case):
    r=report(case);review=r['tax_review']
    assert all(verify(r).values())
    assert review['status']=='conditions_identified'
    assert 'hypothetical_allocation' not in review
    assert all(c['status']=='to_verify' for c in review['conditions'])
    html=render_report_document(r)
    assert 'Sicuramente ti spetta' not in html
    assert 'Da verificare; applicabilità al caso non accertata.' in html
    assert 'Consulta la pagina della pubblicazione' in html
    if review['documentary_context']['purpose']['value']=='renovation':
        ids={c['condition_id'] for c in review['conditions']}
        assert 'renovation_1997' in ids and 'renovation_qualification' in ids
        assert 'purchase_purpose' not in ids
        assert 'Nessun regime selezionato automaticamente' in review['candidate_scope']


@pytest.mark.parametrize('purpose',['primary_home_construction','other'])
def test_context_does_not_assign_purchase_or_renovation_regime(purpose):
    r=report(purpose=purpose);assert all(verify(r).values())
    ids={c['condition_id'] for c in r['tax_review']['conditions']}
    assert 'purchase_purpose' not in ids and 'renovation_1997' not in ids
    if purpose=='other':assert ids=={'paid_year','own_share'}


@pytest.mark.parametrize('fault',['missing','ambiguous','source_failed','unverified','fixture','conflict'])
def test_unusable_context_or_source_produces_no_official_checklist(fault):
    p=profile('C011' if fault=='missing' else 'C001')
    if fault=='ambiguous':p.annual_interest.status='ambiguous'
    a={'status':'failed','error_code':'timeout'}
    if fault=='unverified':a={'status':'unverified','error_code':'missing_provenance'}
    if fault in {'fixture','conflict'}:
        from gateway.tax_evidence import expected_evidence
        from gateway.agent_contracts import TaxView
        a={'status':'completed','result':{'summary':'test','model':'test','evidence':expected_evidence(TaxView(tax_year=int(str(p.tax_year.value)),purpose=p.purpose.value)).model_dump()}}
    if fault=='conflict':
        review=build_tax_review(p,a,has_conflicts=True)
        assert review['reason']=='unresolved_conflict'
    else:
        r=build_report(p,['S-02'],{'S-02':a},a['status']);review=r['tax_review']
        assert all(verify(r).values())
    assert review['status']=='not_assessed' and review['conditions']==[] and 'source' not in review


@pytest.mark.parametrize('change',['quote','page','year','condition_verified','context','missing_condition','question','source_ref','entitlement'])
def test_checker_rejects_changed_or_overstated_report(change):
    r=report();q=r['tax_review'];c=q['conditions'][0]
    if change=='quote':c['source']['quote']='Inventato'
    if change=='page':c['source']['page']=1
    if change=='year':q['source']['tax_year']=2024
    if change=='condition_verified':c['status']='satisfied'
    if change=='context':q['documentary_context']['annual_interest']['value']='1'
    if change=='missing_condition':q['conditions'].pop()
    if change=='question':c['question']='Detrazione garantita'
    if change=='source_ref':c['source']['source_ref']='https://example.org'
    if change=='entitlement':q['tax_entitlement']='entitled'
    assert not all(verify(r).values())


def test_review_cannot_promote_a_source_without_gateway_receipt():
    p=profile('C001')
    a={'status':'completed','result':{'evidence':evidence().model_dump(mode='json')}}
    with pytest.raises(ValueError):build_tax_review(p,a)


def test_html_never_links_to_unconfigured_rule_destination():
    r=report();r['tax_review']['conditions'][0]['source']['source_ref']='javascript:alert(1)'
    assert 'javascript:' not in render_report_document(r)


def test_direct_checker_cli_and_no_new_calculations(tmp_path):
    r=report();path=tmp_path/'report.json';path.write_text(json.dumps(r))
    run=subprocess.run([sys.executable,'scripts/check_tax_review.py',str(path)],capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    assert 'faithful_rule_citations: True' in run.stdout
    p=profile('C001');before=p.model_dump();a={'status':'failed'}
    build_tax_review(p,a);assert before==p.model_dump()


def test_market_only_has_no_tax_review():
    from tests.test_mortgage import profile as mortgage
    r=build_report(mortgage(),['S-01'],{'S-01':{'status':'failed','error_code':'timeout'}},'failed')
    assert r['tax_review'] is None


def test_changed_edition_requires_rule_revision(monkeypatch):
    from gateway.tax_review_rules import EDITION_DIGESTS
    monkeypatch.setitem(EDITION_DIGESTS,'2025','0'*64)
    with pytest.raises(ValueError):report()
