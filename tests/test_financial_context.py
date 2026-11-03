"""Paga/conto: provenienza, minimizzazione e uso reale del percorso locale."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from html import escape
from pathlib import Path
from types import SimpleNamespace
import json

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from gateway.agent_contracts import MarketView, TaxView
from gateway.financial_context import FIELDS, summarize, source_arguments
from gateway.lab_profile import FullFinancialView, full_view
from gateway.models import Scenario
from gateway.pdf_input import PDFInputError, extract_profile
from gateway.policy import domain_view, issues
from gateway.privacy import SensitiveContext, view_paths
from gateway.report import build_report
from gateway.report_document import render_report_document
from scripts.check_financial_context import verify
from scripts.check_report_provenance import verify as provenance

ROOT = Path('dataset/Documents')


def profile(case='C001', kinds=('mutuo', 'interessi', 'conto', 'paga')):
    return extract_profile([(ROOT/f'{case}_{kind}.pdf').read_bytes() for kind in kinds])


def report(p):
    return build_report(p, ['S-01', 'S-02'], {s: {'status': 'blocked', 'error_code': 'input_not_ready'}
                                           for s in ('S-01', 'S-02')}, 'blocked')


@pytest.mark.parametrize('case', [f'C{i:03}' for i in range(1, 26)])
def test_dataset_optional_facts_keep_values_citations_months_and_existing_readiness(case):
    p, summaries = profile(case)
    base, _ = profile(case, ('mutuo', 'interessi'))
    assert all(d['used_for_scenarios'] for d in summaries)
    for scenario in Scenario:
        assert issues(p, scenario) == issues(base, scenario)
    for key in FIELDS:
        f = getattr(p, key)
        assert f.status == 'validated' and f.unit == 'EUR' and f.period_granularity == 'month'
        assert Decimal(str(f.value)) == Decimal(f.source.quote.removesuffix(' EUR').replace('.', '').replace(',', '.'))
        assert f.period == (date(2025, 11, 30) if key == 'payslip_net' else date(2025, 12, 31))
        assert f.period_source.label == 'document_title'
    data = report(p)
    assert all(verify(data).values())
    counted, problems = provenance(data, ROOT)
    assert counted >= 12 and not problems
    html = render_report_document(data)
    assert 'Conto e busta paga — contesto facoltativo' in html
    assert all(escape(getattr(p, key).source.quote) in html for key in FIELDS)
    assert '2025-11' in html and 'reddito ricorrente' in html


@pytest.mark.parametrize('kinds', [('mutuo', 'interessi'), ('mutuo', 'interessi', 'paga'), ('mutuo', 'interessi', 'conto')])
def test_documents_remain_optional_and_missing_context_is_not_invented(kinds):
    p, _ = profile(kinds=kinds)
    data = report(p)
    assert all(verify(data).values())
    context = summarize(p)
    assert (context is None) == (len(kinds) == 2)
    if context:
        assert (context.payslip is not None) == ('paga' in kinds)
        assert (context.account is not None) == ('conto' in kinds)
    for scenario in Scenario:
        assert not issues(p, scenario)


@pytest.mark.parametrize('scenario', list(Scenario))
@pytest.mark.parametrize('full', [False, True])
def test_agents_receive_catalogued_context_but_public_queries_do_not(scenario, full):
    from gateway.market_analysis import build_analysis_input as market, validate_bridge_input as market_validate
    from gateway.tax_analysis import build_analysis_input as tax, validate_bridge_input as tax_validate
    from gateway.market_evidence import expected_evidence as rates
    from gateway.tax_evidence import expected_evidence as fiscal
    p, _ = profile()
    cls = FullFinancialView if full else MarketView if scenario == Scenario.MORTGAGE else TaxView
    view = cls.model_validate(full_view(p) if full else domain_view(p, scenario))
    packet = (market if scenario == Scenario.MORTGAGE else tax)(view, (rates if scenario == Scenario.MORTGAGE else fiscal)(view))
    validate = market_validate if scenario == Scenario.MORTGAGE else tax_validate
    assert validate(packet, unminimized=full) == packet
    selected = [s for s in packet['statements'] if s['statement_id'] in {'context_single_payslip', 'context_single_account'}]
    assert len(selected) == 2
    assert all(path in packet['reference_ids'] for s in selected for path in s['references'])
    if full:
        assert source_arguments(view) == full_view(p)
        assert view.document_context == summarize(p)
    else:
        assert 'document_context' in packet['context']
        assert 'document_context' not in source_arguments(view)
        assert all(str(getattr(p, key).value) not in json.dumps(packet) for key in FIELDS)
        context = SensitiveContext.from_profile(p)
        context.add_documents([(ROOT/'C001_conto.pdf').read_bytes(), (ROOT/'C001_paga.pdf').read_bytes()])
        assert not context.findings(packet['context'], allowed_paths=view_paths())
        # Controllo strutturale: nessun numero in testo libero o importo aggiunto.
        altered = deepcopy(packet['context']); altered['document_context']['payslip']['net_amount'] = '123.45'
        with pytest.raises(ValueError): cls.model_validate(altered)
    changed = deepcopy(packet); changed['statements'][-1]['text'] = 'Il mutuo è sostenibile.'
    with pytest.raises(ValueError): validate(changed, unminimized=full)


@pytest.mark.parametrize('value,sign', [('0', 'zero'), ('-1.50', 'negative'), ('2.50', 'positive')])
def test_zero_and_negative_values_are_not_transformed_into_missing_income_or_income_stability(value, sign):
    p, _ = profile(); p.payslip_net.value = value; p.account_closing_balance.value = value
    reduced = summarize(p)
    assert reduced.payslip.net_sign == sign and reduced.account.closing_balance_sign == sign


@pytest.mark.parametrize('fault', ['missing', 'ambiguous', 'unit', 'non_finite', 'different_period', 'invalid_period'])
def test_unusable_facts_never_enter_comparisons_or_replace_required_mortgage_data(fault):
    p, _ = profile()
    if fault == 'missing': p.account_opening_balance = None
    if fault == 'ambiguous': p.payslip_net.status = 'ambiguous'; p.account_opening_balance.status = 'ambiguous'
    if fault == 'unit': p.payslip_net.unit = 'fraction'; p.account_opening_balance.unit = 'fraction'
    if fault == 'non_finite': p.payslip_net.value = 'NaN'; p.account_opening_balance.value = 'NaN'
    if fault == 'different_period': p.account_opening_balance.period = date(2025, 10, 31)
    if fault == 'invalid_period': p.payslip_net.period = date(9999, 1, 1); p.account_opening_balance.period = date(9999, 1, 1)
    reduced = summarize(p)
    assert reduced.account.balance_change == 'not_comparable'
    if fault in {'ambiguous', 'unit', 'non_finite', 'invalid_period'}: assert reduced.payslip is None
    p.remaining_principal = None
    assert any(i['field'] == 'remaining_principal' for i in issues(p, Scenario.MORTGAGE))


def fake_pdf(monkeypatch, text):
    monkeypatch.setattr('gateway.pdf_input.PdfReader', lambda *a, **kw: SimpleNamespace(is_encrypted=False,
        pages=[SimpleNamespace(extract_text=lambda: text)]))
    return extract_profile([b'%PDF-test'])


def test_parser_uses_competence_month_not_payment_date_and_handles_leap_month(monkeypatch):
    text = 'FACSIMILE SINTETICO\nIBAN di test (non operativo)\nIT00TEST\nProspetto retribuzione febbraio 2024\nNetto\n-10,00 EUR\nAccredito\n02/03/2024\n'
    p, _ = fake_pdf(monkeypatch, text)
    assert p.payslip_net.period == date(2024, 2, 29) and p.payslip_net.value == Decimal('-10.00')
    assert p.payslip_net.period_source.quote == 'Prospetto retribuzione febbraio 2024'


@pytest.mark.parametrize('fault', ['missing_period', 'repeated_period', 'invalid_month', 'repeated_field'])
def test_ambiguous_or_invalid_optional_document_is_rejected_without_guessing(monkeypatch, fault):
    title = 'Estratto conto dicembre 2025'
    text = 'FACSIMILE SINTETICO\nIBAN di test (non operativo)\nIT00TEST\n' + title + '\nSaldo finale\n10,00 EUR\n'
    if fault == 'missing_period': text = text.replace(title, 'Estratto conto senza periodo')
    if fault == 'repeated_period': text += title + '\n'
    if fault == 'invalid_month': text = text.replace('dicembre', 'inventato')
    if fault == 'repeated_field': text += 'Saldo finale\n15,00 EUR\n'
    with pytest.raises(PDFInputError): fake_pdf(monkeypatch, text)


@pytest.mark.parametrize('change', ['value', 'period', 'title_quote', 'title_document', 'label', 'summary', 'claim', 'granularity'])
def test_independent_report_checker_rejects_tampering(change):
    p, _ = profile(); data = report(p); fact = data['financial_context']['facts']['payslip_net']
    if change == 'value': fact['value'] = '999'
    if change == 'period': fact['period'] = '2025-12-31'
    if change == 'title_quote': fact['period_source']['quote'] = 'Prospetto retribuzione dicembre 2025'
    if change == 'title_document': fact['period_source'] = data['financial_context']['facts']['account_closing_balance']['period_source']
    if change == 'label': fact['source']['label'] = 'Lordo'
    if change == 'summary': data['financial_context']['agent_context']['account']['balance_change'] = 'increased'
    if change == 'claim': data['financial_context']['affordability_assessed'] = True
    if change == 'granularity': fact['period_granularity'] = 'day'
    assert not all(verify(data).values())


def test_a2a_mcp_and_both_models_use_supplemental_context_then_clear_session(monkeypatch, local_gateway):
    """ADK/A2A e processi MCP reali; solo la risposta LLM è controllata."""
    from dataclasses import replace
    import httpx
    import gateway.a2a_egress as a2a
    import gateway.market_client as market_client
    import gateway.tax_client as tax_client
    import services.market_agent as markets
    import services.tax_agent as fiscal
    import services.tool_client as tool_client
    import services.inference_client as inference_client
    from gateway.app import create_app
    from gateway.inference import OLLAMA_ENDPOINT
    from scripts.run_ollama_bridge import validate_payload
    original = httpx.AsyncClient
    packets, tool_requests = [], []
    class ControlledModel(httpx.AsyncBaseTransport):
        def __init__(self): self.real = httpx.AsyncHTTPTransport(trust_env=False)
        async def handle_async_request(self, request):
            if str(request.url) == OLLAMA_ENDPOINT:
                payload = json.loads(request.content); validate_payload(payload)
                packet = json.loads(payload['messages'][1]['content']); packets.append(packet)
                tax = packet['evidence']['source_id'] == 'simulated-tax-v1'
                assert packet['context']['document_context']['payslip']['period'] == {'year': 2025, 'month': 11}
                assert any(s['statement_id'] == 'context_single_account' for s in packet['statements'])
                content = {'schema_version': 'tax-selection-1' if tax else 'market-selection-1',
                           'source_statement_ids': ['fixture_documents'] if tax else ['fixture_nature'],
                           'context_statement_id': 'context_single_account' if tax else 'context_single_payslip',
                           'explanation': ''}
                return httpx.Response(200, json={'message': {'content': json.dumps(content)},
                    'prompt_eval_count': 30, 'eval_count': 15, 'load_duration': 0})
            if request.url.path == '/internal/tools/authorize':
                tool_requests.append(json.loads(request.content))
            assert request.url.host == '127.0.0.1'
            return await self.real.handle_async_request(request)
        async def aclose(self): await self.real.aclose()
    def client(**kw):
        if 'transport' not in kw: kw['transport'] = ControlledModel()
        return original(**kw)
    monkeypatch.setattr(httpx, 'AsyncClient', client)
    app = create_app()
    with local_gateway(markets.app) as m, local_gateway(fiscal.app) as t, local_gateway(app) as base:
        routes = dict(a2a.ROUTES)
        routes['S-01'] = replace(routes['S-01'], endpoint=m+'/')
        routes['S-02'] = replace(routes['S-02'], endpoint=t+'/')
        monkeypatch.setattr(a2a, 'ROUTES', routes)
        for module, endpoint in [(market_client, m), (tax_client, t)]:
            monkeypatch.setattr(module, 'ROUTES', routes); monkeypatch.setattr(module, 'ENDPOINT', endpoint+'/')
        monkeypatch.setattr(markets.card, 'url', m+'/'); monkeypatch.setattr(fiscal.card, 'url', t+'/')
        monkeypatch.setattr(tool_client, 'GATEWAY_BASE', base)
        monkeypatch.setattr(inference_client, 'GATEWAY_ENDPOINT', base+'/internal/inference')
        with httpx.Client(base_url=base, trust_env=False, timeout=135) as c:
            files = [('files', (k+'.pdf', (ROOT/f'C001_{k}.pdf').read_bytes())) for k in ('mutuo','interessi','conto','paga')]
            uploaded = c.post('/sessions/pdf', files=files, data={'scenarios':['S-01','S-02']})
            assert uploaded.status_code == 201
            sid = uploaded.json()['session_id']
            response = c.post('/sessions/'+sid+'/analysis')
            assert response.status_code == 200, response.text
            body = response.json(); assert body['status'] == 'completed', body
            data = body['report']; assert all(verify(data).values())
            assert provenance(data, ROOT) == (13, [])
            for generated in data['model_analyses']:
                assert generated['gateway_model_output_receipt_verified']
                assert generated['status'] == 'selection_only'
                assert not generated['semantic_verified']
                selected = generated['selected_statements'][-1]
                assert selected['statement_id'] in {'context_single_account','context_single_payslip'}
                assert all(ref in generated['references'] for ref in selected['references'])
            assert body['session_closed']
            for scenario, recipient in [('S-01','markets'),('S-02','tax')]:
                assert c.post('/sessions/'+sid+'/views', json={'scenario':scenario,'recipient':recipient}).status_code == 404
            assert c.delete('/sessions/'+sid).status_code == 404
    assert len(packets) == 2 and len(tool_requests) == 2
    assert all('document_context' not in req['arguments'] for req in tool_requests)
    assert not markets.task_store.tasks and not fiscal.task_store.tasks


def test_month_year_exceptions_do_not_allow_exact_amounts_or_free_text():
    context = SensitiveContext(amounts={Decimal('2025'), Decimal('11'), Decimal('1934.86')})
    allowed = {'document_context': {'payslip': {'period': {'year':2025, 'month':11}, 'net_sign':'positive'}}}
    assert not context.findings(allowed, allowed_paths=view_paths())
    for forbidden in [
        {'document_context': {'payslip': {'period': {'year':'2025', 'month':11}}}},
        {'document_context': {'payslip': {'net_amount':'1934.86'}}},
        {'query':'1934.86'}, {'document_context':{'2025':'ok'}}]:
        assert context.findings(forbidden, allowed_paths=view_paths())


@pytest.mark.parametrize('organization', ['single', 'multi'])
@pytest.mark.parametrize('minimization', ['active', 'disabled'])
def test_optional_documents_in_four_experimental_cells(organization, minimization):
    import os, subprocess, sys
    code = '''
from contextlib import ExitStack
from fastapi.testclient import TestClient
from tests import block2_worker as w
from scripts.check_block1 import verify_report,expected_activities
from scripts.check_financial_context import verify
with ExitStack() as stack:
    for agent in {id(a):a for a in w.agents.values()}.values():
        stack.enter_context(TestClient(agent))
    stack.enter_context(w.serve())
    client=stack.enter_context(TestClient(w.app))
    for case in ('C001','C006'):
        body,trace=w.execute(client,case,kinds=('mutuo','interessi','conto','paga'))
        assert body['status']==('completed' if case=='C001' else 'partial'),body
        assert all(verify(body['report']).values())
        checks=verify_report(body['report'],expected_activities(case),real_sources=False,minimization=w.runtime.MINIMIZATION)
        assert all(checks.values()), {k:v for k,v in checks.items() if not v}
        for activity in body['activities'].values():
            if activity['status']!='completed':continue
            m=activity['result']['measurements']
            if w.runtime.UNMINIMIZED:
                assert m['a2a_view_exact_amount_fields']==m['model_context_exact_amount_fields']==m['mcp_arguments_exact_amount_fields']==(6 if case=='C001' else 5)
            else:
                assert m['a2a_view_exact_amount_fields']==m['model_context_exact_amount_fields']==m['mcp_arguments_exact_amount_fields']==0
                assert m['mcp_arguments_bytes']<m['a2a_view_bytes']==m['model_context_bytes']
print('passed: True')
'''
    env = {**os.environ, 'TESI_RUNTIME':'local', 'TESI_EXPERIMENT':organization,
        'TESI_MINIMIZATION':minimization, 'TESI_SHARED_REFERENCE':'1', 'TESI_VERIFICATION_PROFILE':'nominal',
        'TESI_MARKET_SOURCE':'simulated', 'TESI_TAX_SOURCE':'simulated', 'TESI_MCP_PROFILE':'nominal',
        'TESI_MARKET_TOOL_IMPLEMENTATION':'standard'}
    result = subprocess.run([sys.executable,'-c',code], env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout[-1500:]+result.stderr[-4000:]
    assert 'passed: True' in result.stdout
