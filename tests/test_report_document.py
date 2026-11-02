"""Il documento deve conservare dati, limiti ed esiti del JSON senza nuove conclusioni."""
import json
from pathlib import Path
from html import unescape
from html.parser import HTMLParser
import pytest
from fastapi.testclient import TestClient
from gateway.report import build_report
from gateway.report_document import render_report_document, number
from gateway.pdf_input import extract_profile
from gateway.agent_contracts import MarketTask,MarketResult,TaxResult
from gateway.market_evidence import expected_evidence as market
from gateway.tax_evidence import expected_evidence as tax
from gateway.agent_contracts import MarketView,TaxView
from gateway.models import Scenario
from gateway.policy import make_view,issues


def report(case='C001'):
    profile,_=extract_profile([Path(f'dataset/Documents/{case}_{k}.pdf').read_bytes() for k in ('mutuo','interessi')])
    activities={}
    for scenario in ('S-01','S-02'):
        blocked=bool(issues(profile,Scenario(scenario)))
        activities[scenario]={'status':'blocked' if blocked else 'completed','error_code':'input_not_ready' if blocked else None}
        if not blocked:
            evidence=market(MarketView.model_validate(make_view(profile,Scenario.MORTGAGE))) if scenario=='S-01' else tax(TaxView.model_validate(make_view(profile,Scenario.TAX)))
            activities[scenario]['result']={'evidence':evidence.model_dump(mode='json'),'summary':'Prosa non verificata da non pubblicare','model':'fixture','limits':[]}
    status='completed' if all(a['status']=='completed' for a in activities.values()) else 'partial'
    return build_report(profile,['S-01','S-02'],activities,status)


@pytest.mark.parametrize('case',['C001','C024','C006','C011','C016'])
def test_document_preserves_success_partial_and_fidelity(case):
    data=report(case);html=render_report_document(data)
    assert 'fonti di questa versione sono simulate' in html
    assert 'Nessuna detrazione o spettanza fiscale' in html
    assert 'Prosa non verificata da non pubblicare' not in html
    assert all(unescape(str(statement['text'])) in unescape(html) for summary in data['faithful_summaries'] for statement in summary['statements'])
    for section in data['document_data']:
        for name,fact in section['facts'].items():
            if fact.get('unit')=='EUR':assert number(fact['value']) in html
            if fact.get('unit')=='year':assert str(fact['value']) in html and '2.025' not in html
            if fact.get('source',{}).get('quote'):assert fact['source']['quote'] in unescape(html)
    if case=='C006':assert 'Confronto non calcolato' in html
    if case=='C011':assert 'Ripartizione non calcolata' in html
    if case=='C024':assert 'tasso congelato' in html


def test_document_does_not_execute_source_text():
    data=report();attack='<script>alert("private")</script><img src=x onerror=alert(1)>'
    data['document_data'][0]['facts']['remaining_principal']['source']['quote']=attack
    data['limits'].append(attack)
    html=render_report_document(data)
    assert '<script>' not in html and '<img ' not in html
    assert '&lt;script&gt;' in html
    assert attack in unescape(html)


def test_number_keeps_precision_and_sign_without_float_calculation():
    assert number('12345678901234567890.123456')=='12.345.678.901.234.567.890,123456'
    assert number('-4.03')=='-4,03'


def test_api_keeps_json_and_cleanup_if_presentation_fails(monkeypatch):
    from gateway.app import create_app
    import gateway.market_client as client
    async def delegate(task):return MarketResult(correlation_id=task.correlation_id,status='completed',evidence=market(task.view),summary='Demo',limits=[],model='test')
    def broken(_):raise ValueError('private contents')
    monkeypatch.setattr(client,'delegate',delegate)
    monkeypatch.setattr('gateway.report_document.render_report_document',broken)
    with TestClient(create_app()) as c:
        data=json.loads(Path('examples/session_complete.json').read_text());data['scenarios']=['S-01']
        sid=c.post('/sessions',json=data).json()['session_id']
        response=c.post('/sessions/'+sid+'/analysis')
        assert response.status_code==200
        body=response.json()
        assert body['report']['status']=='completed' and body['report_document_html'] is None
        assert 'private contents' not in response.text
        assert body['presentation_warning'] and c.delete('/sessions/'+sid).status_code==404


@pytest.mark.parametrize('case,missing',[('C006','Capitale residuo'),('C011','Interessi annui documentati'),('C016','Tasso annuo contrattuale')])
def test_partial_report_highlights_unusable_fields_without_losing_other_domain(case,missing):
    from gateway.report_document import report_alerts
    data=report(case)
    alerts=report_alerts(data)
    assert any(tone=='error' and missing in ' '.join(details) for tone,title,details in alerts)
    html=render_report_document(data)
    assert 'tone-error' in html and '! '+missing in html
    assert len(data['document_data'])==2
    assert any(o['status']=='completed' for o in data['outcomes'])


def test_optional_context_and_different_domain_periods_are_not_red_errors():
    from gateway.report_document import report_alerts
    data=report('C021')
    assert data['document_data'][0]['facts']['annual_rate']['period']!=data['document_data'][1]['facts']['tax_year']['period']
    assert not any(tone=='error' for tone,_,_ in report_alerts(data))
    assert any(tone=='warning' and 'Tipologia del mutuo' in ' '.join(details) for tone,_,details in report_alerts(data))
    assert 'class="tone-error"' not in render_report_document(data)


def test_conflict_keeps_both_values_provenance_and_suspension_without_mutation():
    from copy import deepcopy
    from gateway.comparisons import Observation,evaluate
    data=report()
    data['consistency']=evaluate([Observation(observation_id='a',quantity='aggregate_aar_nder',product='SIMULATED_PRESENTATION_PRODUCT',period='2025-01',value='3',unit='percent_per_year',source_kind='agent',source_ref='simulated-a',verified=True),Observation(observation_id='b',quantity='aggregate_aar_nder',product='SIMULATED_PRESENTATION_PRODUCT',period='2025-01',value='4',unit='percent_per_year',source_kind='agent',source_ref='simulated-b',verified=True)])
    before=deepcopy(data);html=unescape(render_report_document(data))
    assert data==before
    assert 'Conflitto da risolvere' in html and 'conclusioni applicative sono sospese' in html
    for part in ['3 percent_per_year','4 percent_per_year','simulated-a','simulated-b','2025-01','SIMULATED_PRESENTATION_PRODUCT']:
        assert part in html


def test_tax_only_reference_provenance_is_retained(monkeypatch):
    from gateway import verification_config
    from gateway.shared_reference import expected
    monkeypatch.setattr(verification_config,'PROFILE','nominal')
    profile,_=extract_profile([Path('dataset/Documents/C001_interessi.pdf').read_bytes()])
    evidence=tax(TaxView.model_validate(make_view(profile,Scenario.TAX)))
    reference=expected('S-02').model_dump(mode='json')
    result={'evidence':evidence.model_dump(mode='json'),'summary':'controlled','model':'fixture','reference':reference,'measurements':{'gateway_reference_receipt_verified':1}}
    data=build_report(profile,['S-02'],{'S-02':{'status':'completed','result':result}},'completed')
    assert len(data['comparison_references'])==1
    assert data['comparison_references'][0]['scenario']=='S-02'
    assert data['comparison_references'][0]['evidence']==reference
    assert data['comparison_references'][0]['institutional_live_retrieval'] is False
    html=render_report_document(data)
    assert reference['source_id'] in html


@pytest.mark.parametrize('name,kind',[('app.css','text/css'),('app.js','text/javascript'),('ui_state.js','text/javascript')])
def test_only_explicit_ui_assets_are_served(name,kind):
    from gateway.app import create_app
    with TestClient(create_app()) as client:
        response=client.get('/static/'+name)
        assert response.status_code==200 and response.headers['content-type'].startswith(kind)
        assert response.content==Path('gateway/static',name).read_bytes()
        assert response.headers['cache-control']=='no-store'
        for forbidden in ['identity.json','app.py','../app.py','%2e%2e%2fapp.py']:
            assert client.get('/static/'+forbidden).status_code==404


def test_trace_polling_uses_no_store_and_never_mutates_or_exposes_profile():
    from gateway.app import create_app
    with TestClient(create_app()) as client:
        payload=json.loads(Path('examples/session_complete.json').read_text())
        response=client.post('/sessions',json=payload)
        sid=response.json()['session_id'];identifier=response.json()['trace_id']
        first=client.get('/traces/'+identifier)
        assert first.headers['cache-control']=='no-store'
        assert not first.json()['profile_closed']
        assert client.get('/traces/'+identifier).json()==first.json()
        assert 'remaining_principal' not in first.text and 'annual_interest' not in first.text
        assert client.delete('/sessions/'+sid).status_code==204
        last=client.get('/traces/'+identifier)
        assert last.headers['cache-control']=='no-store' and last.json()['profile_closed']


def test_incoherent_periods_inside_contract_are_red_without_rewriting_dates():
    from datetime import date
    from gateway.report_document import report_alerts
    profile,_=extract_profile([Path(f'dataset/Documents/C001_{kind}.pdf').read_bytes() for kind in ('mutuo','interessi')])
    profile.remaining_months.period=date(2024,12,31)
    activities={'S-01':{'status':'blocked','error_code':'input_not_ready'},'S-02':{'status':'blocked','error_code':'input_not_ready'}}
    data=build_report(profile,['S-01','S-02'],activities,'blocked')
    assert any(tone=='error' and 'Date contrattuali non allineate' in details for tone,_,details in report_alerts(data))
    assert data['document_data'][0]['facts']['remaining_months']['period']=='2024-12-31'
    assert data['document_data'][0]['facts']['annual_rate']['period']=='2025-12-31'
    html=render_report_document(data)
    assert 'Date contrattuali non allineate' in html and 'tone-error' in html
