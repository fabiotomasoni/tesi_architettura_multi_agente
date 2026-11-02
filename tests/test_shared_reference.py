"""Ricevute comuni: fedeltà, origine esplicita e capability separate."""
import asyncio,json
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid4
import pytest
from gateway import verification_config as config
from gateway.agent_contracts import MarketTask,MarketResult
from gateway.a2a_egress import EgressDenied
from gateway.inference import InferenceBroker
from gateway.shared_reference import expected,verify,observation,TOOL,DESTINATION
from gateway.tool_egress import ToolRequest,SourceRequest,authorize_tool,source_request
from gateway.comparisons import compare

@pytest.mark.parametrize('profile',['nominal','conflict_agents','conflict_document','equivalent_units','different_period','different_product'])
def test_receipts_are_explicit_and_comparisons_preserve_semantics(profile):
    observations=[]
    for scenario in ['S-01','S-02']:
        receipt=expected(scenario,profile);raw=receipt.model_dump(mode='json')
        checked,digest=verify(raw,scenario,profile)
        assert len(digest)==64 and checked==receipt
        assert (receipt.origin=='recorded_official_response_replay')==(profile=='nominal')
        assert (receipt.recorded_evidence is not None)==(profile=='nominal')
        observations.append(observation(receipt,scenario))
    result=compare(*observations)
    assert result['status']=={'conflict_agents':'conflict','different_period':'not_comparable','different_product':'not_comparable'}.get(profile,'consistent')

@pytest.mark.parametrize('field',['value','unit','period','quantity','product','source_id','origin','recorded_evidence','fixture_profile','version'])
def test_missing_or_altered_receipt_is_never_repaired(field):
    raw=expected('S-01').model_dump(mode='json');raw.pop(field)
    with pytest.raises(ValueError):verify(raw,'S-01')
    raw=expected('S-01').model_dump(mode='json');raw[field]='forged'
    with pytest.raises(ValueError):verify(raw,'S-01')

def test_runtime_reference_is_the_same_pinned_public_snapshot():
    assert Path('gateway/fixtures/ecb_reference.json').read_bytes()==Path('tests/fixtures/ecb_mir_public_response.json').read_bytes()

def test_reference_has_independent_single_use_permit_and_empty_arguments(monkeypatch):
    monkeypatch.setattr(config,'SHARED',True);monkeypatch.setattr(config,'PROFILE','nominal')
    broker=InferenceBroker();task=MarketTask(correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'mortgage_type':'not_specified','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
    async def remote(t):
        auth='Bearer '+t.inference_token
        req=ToolRequest(correlation_id=t.correlation_id,scenario='S-01',tool=TOOL,arguments={})
        permit=authorize_tool(broker,req,auth)
        assert permit.arguments=={} and permit.destination==DESTINATION
        with pytest.raises(EgressDenied):authorize_tool(broker,req,auth)
        source=SourceRequest(**req.model_dump(),destination=permit.destination,headers={})
        raw=await source_request(broker,source,'Bearer '+permit.source_token)
        with pytest.raises(EgressDenied):await source_request(broker,source,'Bearer '+permit.source_token)
        with pytest.raises(EgressDenied):await source_request(broker,source,auth)
        # Leggere il riferimento non consuma il permesso di dominio.
        domain=ToolRequest(correlation_id=t.correlation_id,scenario='S-01',tool='lookup_rates',arguments=t.view.model_dump(mode='json'))
        assert authorize_tool(broker,domain,auth).tool=='lookup_rates'
        from types import SimpleNamespace
        return SimpleNamespace(measurements={},reference=None)
    asyncio.run(broker.delegate(uuid4(),task,remote))
    assert not broker._grants
