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
