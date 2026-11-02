"""Il pilota ricontrolla dati e cataloghi: nessuna chiamata Internet o modello."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from gateway.agent_contracts import MarketView,TaxView
from gateway.pdf_input import extract_profile
from gateway.models import Scenario
from gateway.policy import domain_view
from gateway.report import build_report
from gateway.market_analysis import review_for_display as market_review
from gateway.tax_analysis import review_for_display as tax_review
from scripts.check_block1 import verify_report,expected_activities,CASES
from tests.test_ecb_source import evidence as ecb
from tests.test_ade_source import evidence as ade


def complete_report(case):
    p=extract_profile([Path('dataset/Documents',case+'_'+k+'.pdf').read_bytes() for k in ('mutuo','interessi')])[0]
    expected=expected_activities(case);activities={}
    for scenario,state in expected.items():
        if state=='blocked':activities[scenario]={'status':'blocked','error_code':'input_not_ready'};continue
        fiscal=scenario=='S-02'
        view=(TaxView if fiscal else MarketView).model_validate(domain_view(p,Scenario(scenario)))
        evidence=ade(view.tax_year,view.purpose) if fiscal else ecb()
        choice={'schema_version':'tax-selection-1' if fiscal else 'market-selection-1',
                'source_statement_ids':['paid_year','own_share'] if fiscal else ['source_value','ecb_not_personal_offer'],
                'context_statement_id':'context_tax_year' if fiscal else 'context_rate_'+view.rate_type,
                'explanation':''}
        generated=(tax_review if fiscal else market_review)(json.dumps(choice),view,evidence)
        assert generated['status']=='selection_only'
        activities[scenario]={'status':'completed','result':{'model':'controlled','evidence':evidence.model_dump(mode='json'),
            'summary':'Non usata come evidenza','limits':[],
            'tax_analysis' if fiscal else 'market_analysis':generated,
            'measurements':{'gateway_source_receipt_verified':1,'gateway_analysis_receipt_verified':1}}}
    return build_report(p,['S-01','S-02'],activities,'completed' if all(v=='completed' for v in expected.values()) else 'partial')


@pytest.mark.parametrize('case',CASES)
def test_all_demo_cases_check_citations_pdfs_and_model_selection(case):
    checks=verify_report(complete_report(case),expected_activities(case))
    assert all(checks.values()),{k:v for k,v in checks.items() if not v}


@pytest.mark.parametrize('change',['source_quote','page','year','selection_text','selection_id','source_digest',
                                   'receipt','entitlement','lost_condition','invented_interest','semantic_claim','model_inventory'])
def test_checker_cannot_succeed_on_changed_or_overstated_report(change):
    report=deepcopy(complete_report('C001'))
    analysis=next(x for x in report['model_analyses'] if x['scenario']=='S-02')
    condition=analysis['selected_statements'][0]
    if change=='source_quote':condition['source']['quote']='Un estratto inventato'
    if change=='page':condition['source']['page']=1
    if change=='year':condition['source']['tax_year']=2024
    if change=='selection_text':condition['text']='La condizione è soddisfatta'
    if change=='selection_id':analysis['content']['source_statement_ids']=['unknown']
    if change=='source_digest':analysis['source_sha256']='0'*64
    if change=='receipt':analysis['gateway_model_output_receipt_verified']=False
    if change=='entitlement':analysis['tax_entitlement']='entitled'
    if change=='lost_condition':report['tax_review']['conditions'].pop()
    if change=='invented_interest':next(s for s in report['document_data'] if s['scenario']=='S-02')['facts']['annual_interest']['value']='1'
    if change=='semantic_claim':analysis['semantic_verified']=True
    if change=='model_inventory':report['model_analyses'].append(deepcopy(analysis))
    assert not all(verify_report(report,expected_activities('C001')).values())


def test_direct_command_help_and_existing_output_are_safe(tmp_path):
    run=subprocess.run([sys.executable,'scripts/check_block1.py','--help'],capture_output=True,text=True)
    assert run.returncode==0 and '--reports-dir' in run.stdout
    output=tmp_path/'already.json';output.write_text('intatto')
    run=subprocess.run([sys.executable,'scripts/check_block1.py','--output',str(output)],capture_output=True,text=True)
    assert run.returncode==2 and output.read_text()=='intatto'
