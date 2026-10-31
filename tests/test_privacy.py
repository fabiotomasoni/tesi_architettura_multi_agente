"""Casi sintetici annotati: contenuti vietati e controlli negativi separati."""
from decimal import Decimal
import asyncio
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from gateway.privacy import SensitiveContext,check,normalize
from gateway.a2a_egress import EgressDenied
from gateway.inference import InferenceBroker
from gateway.agent_contracts import MarketTask
from gateway.tool_egress import ToolRequest,authorize_tool


def context():
    return SensitiveContext(entities={'marco riva','it00x0000000000000000000001'},amounts={Decimal('90434.57')},dates={'2025-12-31'})


@pytest.mark.parametrize('text',[
 'Marco&#32;Riva',"90’434,57",'20251231','2025-12-31T12:00:00',
 'Marco Riva','MARCO  RIVA','Marco\u200b Riva','%4darco%20Riva',
 '90434.57','90.434,57 EUR','90 434,57','９０４３４．５７',
 '2025-12-31','31/12/2025','31.12.2025',
 'persona@example.invalid','RSSMRA85A01F205X','IT00 X000 0000 0000 0000 0000 0001'])
def test_forbidden(text):
    assert context().findings(text)
    with pytest.raises(EgressDenied):check(context(),{'query':text})


@pytest.mark.parametrize('value',[
 {'tax_year':2025},{'lower_exclusive':5,'upper_inclusive':10},
 {'rate_type':'fixed'},{'purpose':'renovation'},'Ricerca normativa per anno',
 'tasso simulato 3.20%', '1900', '90434.58'])
def test_legitimate(value):assert not context().findings(value)


def test_nested_keys_headers_url_and_values():
    for payload in [{'Marco Riva':'ok'},{'headers':{'X-Test':'90434.57'}},
                    {'url':'https://source.invalid/?name=Marco%20Riva'},['ok',{'text':'31/12/2025'}]]:
        assert context().findings(payload)


def test_context_extracts_entities_without_retaining_documents():
    c=SensitiveContext();c.add_documents([Path('dataset/Documents/C001_mutuo.pdf').read_bytes()])
    assert 'known_entity' in c.findings('Marco Riva')
    assert 'known_amount' in c.findings('90434.57')
    assert 'known_date' in c.findings('31.12.2025')
    assert not hasattr(c,'documents') and 'Marco' not in repr(c)


def test_session_context_revoked():
    broker=InferenceBroker();sid=uuid4();broker._privacy[sid]=context()
    broker.revoke(sid);assert sid not in broker._privacy


def test_schema_valid_string_with_forbidden_value_denied_before_tool():
    broker=InferenceBroker();sid=uuid4();broker._privacy[sid]=context()
    task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
    async def remote(t):
        r=ToolRequest(correlation_id=t.correlation_id,scenario=t.scenario,tool='lookup_rates',arguments={'query':'Marco Riva'})
        with pytest.raises(EgressDenied,match='known_entity'):authorize_tool(broker,r,'Bearer '+t.inference_token)
        assert not broker._grants[t.inference_token].tool_used
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(sid,task,remote))


def test_annotated_independent_corpus():
    from scripts.check_privacy import annotated_pilot, dataset_pilot
    result=annotated_pilot()
    assert result['counts']['false_positive']==0
    assert result['counts']['false_negative']==0
    assert dataset_pilot()=={'legitimate_views':35,'legitimate_blocked':0}


def test_authorized_numeric_paths_do_not_exempt_free_text_or_keys():
    from gateway.privacy import view_paths
    c=SensitiveContext(amounts={Decimal('2024'),Decimal('5'),Decimal('10')})
    assert not c.findings({'tax_year':2024},allowed_paths=view_paths())
    assert not c.findings({'remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}},allowed_paths=view_paths())
    for value in [{'query':2024},{'tax_year':'2024'},{'headers':{'tax_year':2024}},{'2024':'ok'}]:
        assert 'known_amount' in c.findings(value,allowed_paths=view_paths())


@pytest.mark.parametrize('text',['mi chiamo Elena Bianchi','cliente: Lucia Verdi','via delle Rose 17','Tecnologie Alpine SRL'])
def test_new_entities_detected_without_dataset_label(text):
    assert 'local_entity_candidate' in SensitiveContext().findings(text)


def test_partial_known_name_and_scientific_amount():
    c=SensitiveContext();c.add_documents([Path('dataset/Documents/C001_mutuo.pdf').read_bytes()])
    assert 'known_entity' in c.findings('Riva')
    assert 'known_amount' in c.findings('9.043457e4 EUR')


def test_entity_heuristic_limit_is_explicit_not_anonymity_claim():
    # Senza conoscenza della sessione o indizi contestuali il filtro può mancare un nome.
    assert not SensitiveContext().findings('elena bianchi')


@pytest.mark.parametrize('fiscal',[False,True])
def test_collision_does_not_break_authorized_whole_broker_path(monkeypatch,fiscal):
    import httpx
    from gateway.agent_contracts import TaxTask
    from gateway.inference import InferenceRequest
    from gateway.tool_egress import SourceRequest,source_request
    from gateway.market_evidence import expected_evidence as market
    from gateway.tax_evidence import expected_evidence as tax
    broker=InferenceBroker();sid=uuid4()
    broker._privacy[sid]=SensitiveContext(amounts={Decimal('2025'),Decimal('5'),Decimal('10'),Decimal('3.20')},dates={'2025-12-31'})
    base=dict(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60))
    task=(TaxTask(**base,view={'tax_year':2025,'purpose':'renovation'}) if fiscal else MarketTask(**base,view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}}))
    sent=[];original=httpx.AsyncClient
    def receive(request):
        sent.append(request)
        return httpx.Response(200,json={'message':{'content':'Simulazione'},'prompt_eval_count':1,'eval_count':1,'load_duration':0})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(receive),**kw))
    async def remote(t):
        name='lookup_tax' if fiscal else 'lookup_rates'
        req=ToolRequest(correlation_id=t.correlation_id,scenario=t.scenario,tool=name,arguments=t.view.model_dump(mode='json'))
        permit=authorize_tool(broker,req,'Bearer '+t.inference_token)
        evidence=await source_request(broker,SourceRequest(**req.model_dump(),destination=permit.destination,headers={}), 'Bearer '+permit.source_token)
        result=await broker.infer(InferenceRequest(correlation_id=t.correlation_id,scenario=t.scenario,evidence=evidence),'Bearer '+t.inference_token)
        assert result.output_tokens==1
        return SimpleNamespace(measurements={})
    result=asyncio.run(broker.delegate(sid,task,remote))
    assert len(sent)==1 and result.measurements['gateway_inference_completed']==1
    broker.revoke(sid);assert not broker._privacy and not broker._grants


@pytest.mark.parametrize('text',['mi chiamo elena bianchi','+39 02 8123 4567','tel: 333 1234567','31122025'])
def test_more_local_identifiers(text):
    assert context().findings(text)


def test_denial_before_source_transport_and_without_sensitive_error(monkeypatch):
    from gateway.tool_egress import SourceRequest,source_request
    import httpx
    broker=InferenceBroker();sid=uuid4();broker._privacy[sid]=context()
    task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
    def forbidden_transport(**kwargs):
        pytest.fail('Nessun trasporto HTTP deve essere aperto dopo il diniego')
    monkeypatch.setattr(httpx,'AsyncClient',forbidden_transport)
    async def remote(t):
        req=ToolRequest(correlation_id=t.correlation_id,scenario=t.scenario,tool='lookup_rates',arguments=t.view.model_dump(mode='json'))
        permit=authorize_tool(broker,req,'Bearer '+t.inference_token)
        request=SourceRequest(**req.model_dump(),destination=permit.destination,headers={'X-Note':'Marco Riva'})
        with pytest.raises(EgressDenied) as error:
            await source_request(broker,request,'Bearer '+permit.source_token)
        assert 'Marco' not in str(error.value) and 'Riva' not in str(error.value)
        grant=broker._grants[t.inference_token]
        assert not grant.source_used and not grant.used
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(sid,task,remote))


def test_missing_scanner_entity_still_rejected_by_closed_catalog():
    broker=InferenceBroker();sid=uuid4()
    task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
    async def remote(t):
        args=t.view.model_dump(mode='json');args['query']='elena bianchi'
        assert not SensitiveContext().findings(args['query'])
        req=ToolRequest(correlation_id=t.correlation_id,scenario=t.scenario,tool='lookup_rates',arguments=args)
        with pytest.raises(EgressDenied):authorize_tool(broker,req,'Bearer '+t.inference_token)
        assert not broker._grants[t.inference_token].tool_used
        return SimpleNamespace(measurements={})
    asyncio.run(broker.delegate(sid,task,remote))


def test_document_context_failure_does_not_publish_session(monkeypatch):
    from fastapi.testclient import TestClient
    from gateway.app import create_app
    import importlib
    app_module=importlib.import_module('gateway.app')
    broker=InferenceBroker()
    monkeypatch.setattr(app_module,'InferenceBroker',lambda:broker)
    def fail(*args):raise RuntimeError('private document text')
    monkeypatch.setattr(SensitiveContext,'add_documents',fail)
    with TestClient(create_app()) as client:
        response=client.post('/sessions/pdf',files=[('files',('document.pdf',Path('dataset/Documents/C001_mutuo.pdf').read_bytes(),'application/pdf'))],data={'scenarios':'S-01'})
        assert response.status_code==400 and 'private document text' not in response.text
        assert not broker._privacy and not broker._grants


@pytest.mark.parametrize('mode',['delete','expiry','shutdown'])
def test_api_context_cleanup(monkeypatch,mode):
    import importlib,json
    from fastapi.testclient import TestClient
    from gateway.app import create_app
    app_module=importlib.import_module('gateway.app');broker=InferenceBroker()
    monkeypatch.setattr(app_module,'InferenceBroker',lambda:broker)
    if mode=='expiry':monkeypatch.setattr(app_module,'SESSION_TTL_SECONDS',-1)
    with TestClient(create_app()) as client:
        response=client.post('/sessions',json=json.loads(Path('examples/session_complete.json').read_text()))
        assert response.status_code==201 and broker._privacy
        sid=response.json()['session_id']
        if mode!='shutdown':
            client.delete('/sessions/'+sid)
            assert not broker._privacy
    assert not broker._privacy and not broker._grants


def test_entity_collection_keeps_line_boundaries():
    c=SensitiveContext();c.add_documents([Path('dataset/Documents/C001_mutuo.pdf').read_bytes()])
    assert not c.findings('anno fiscale 2023')
    assert 'fiscale' not in c.entities and 'intestatario' not in c.entities


def test_trusted_public_exemption_never_exempts_entity_patterns():
    c=context()
    with pytest.raises(EgressDenied):
        check(c,{'reference_date':'persona@example.invalid'},public_paths=frozenset({('reference_date',)}))


def test_health_identifies_filter_loaded():
    from fastapi.testclient import TestClient
    from gateway.app import create_app
    from gateway.privacy import PRIVACY_VERSION,ENTITY_RECOGNIZER_VERSION
    with TestClient(create_app()) as client:
        result=client.get('/health').json()
        assert result['privacy_version']==PRIVACY_VERSION
        assert result['entity_recognizer_version']==ENTITY_RECOGNIZER_VERSION
