import copy
from pathlib import Path
import pytest
from gateway.pdf_input import extract_profile
from gateway.report import build_report
from gateway.policy import make_view,OPTIONAL,REQUIRED
from gateway.models import Scenario
from scripts.check_report_provenance import verify

ROOT=Path('dataset/Documents')


def report(case):
    profile,_=extract_profile([(ROOT/f'{case}_mutuo.pdf').read_bytes(),(ROOT/f'{case}_interessi.pdf').read_bytes()])
    activities={s:{'status':'blocked','error_code':'test'} for s in ['S-01','S-02']}
    return build_report(profile,['S-01','S-02'],activities,'blocked')


@pytest.mark.parametrize('number',range(1,26))
def test_all_facts_match_pdf_spans_and_transformations(number):
    data=report(f'C{number:03}')
    checked,problems=verify(data,ROOT)
    assert not problems,problems
    assert checked>=9
    for section in data['document_data']:
        assert set(section['facts'])==set(REQUIRED[Scenario(section['scenario'])]+OPTIONAL[Scenario(section['scenario'])])
    assert data['document_data'][0]['facts']['mortgage_type']=={'status':'not_specified'}


@pytest.mark.parametrize('tamper',['value','quote','offset','period','omit','section'])
def test_verifier_rejects_report_tampering(tamper):
    data=report('C001')
    fact=data['document_data'][0]['facts']['remaining_principal']
    if tamper=='value':fact['value']='1'
    elif tamper=='quote':fact['source']['quote']='inventato'
    elif tamper=='offset':fact['source']['start']+=1
    elif tamper=='period':fact['period']='2024-12-31'
    elif tamper=='omit':del data['document_data'][0]['facts']['annual_rate']
    else:data['document_data'].pop()
    assert verify(data,ROOT)[1]


def test_missing_and_ambiguous_are_visible_without_fabricated_values():
    missing=report('C006')
    assert missing['completeness'][0]['missing_required']==['remaining_principal']
    ambiguous=report('C016')
    assert 'annual_rate' in ambiguous['completeness'][0]['ambiguous_or_unvalidated']
    fact=ambiguous['document_data'][0]['facts']['annual_rate']
    assert 'oppure' in fact['source']['quote']
    assert fact['status']=='ambiguous'


def test_view_never_contains_local_citations():
    profile,_=extract_profile([(ROOT/'C001_mutuo.pdf').read_bytes()])
    view=make_view(profile,Scenario.MORTGAGE)
    assert view['mortgage_type']=='not_specified'
    assert set(view)=={'mortgage_type','rate_type','remaining_years_band'}


def test_verifier_rejects_existing_field_falsely_marked_missing():
    data=report('C001')
    data['document_data'][0]['facts']['remaining_principal']={'status':'missing'}
    assert verify(data,ROOT)[1]
