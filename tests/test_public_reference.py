"""Contratto sullo snapshot BCE già acquisito; nessuna nuova richiesta web."""
import json
from pathlib import Path

import pytest

from gateway.comparisons import Observation,compare,ecb_reference_observation
from gateway.ecb_source import parse_csv


def receipt():
    data=json.loads(Path('tests/fixtures/ecb_mir_public_response.json').read_text())
    row=parse_csv(data['source_csv'])
    from gateway.ecb_source import EcbRateEvidence
    return EcbRateEvidence(annual_rate_percent=row['OBS_VALUE'],observation_period=row['TIME_PERIOD'],
        source_csv=data['source_csv'],retrieved_at=data['retrieved_at'],
        response_sha256=data['response_sha256']).model_dump(mode='json')


def test_public_reference_preserves_actual_recorded_value_period_and_definition():
    evidence=receipt()
    first=ecb_reference_observation(evidence,'S-01')
    second=ecb_reference_observation(evidence,'S-02')
    assert first.value==evidence['annual_rate_percent']
    assert first.period==evidence['observation_period']  # Mese, senza giorno inventato.
    assert first.quantity=='aggregate_aar_nder' and first.product=='Italy_new_house_purchase_loans'
    assert first.unit=='percent_per_year' and first.source_ref.endswith('#'+first.period)
    assert first.observation_id!=second.observation_id
    assert compare(first,second)['status']=='consistent'


@pytest.mark.parametrize('field',['annual_rate_percent','observation_period','response_sha256','source_csv','source_url'])
def test_common_contract_rejects_unfaithful_or_missing_receipt(field):
    data=receipt()
    if field=='annual_rate_percent':data[field]='9.99'
    elif field=='observation_period':data[field]='2000-01'
    else:del data[field]
    with pytest.raises(ValueError):ecb_reference_observation(data,'S-02')


def test_aggregate_public_reference_is_not_comparable_to_personal_contract_rate():
    public=ecb_reference_observation(receipt())
    contract=Observation(observation_id='document-contract-rate',quantity='contract_annual_rate',
        product=public.product,period=public.period,value=public.value,unit=public.unit,
        source_kind='document',source_ref='controlled-document',verified=True)
    assert compare(public,contract)['reason']=='quantity_mismatch'


def test_different_month_does_not_become_a_numeric_conflict():
    # Solo controllo del comparatore: non modifica una ricevuta istituzionale.
    first=ecb_reference_observation(receipt())
    second=first.model_copy(update={'observation_id':'historical-public-observation','period':'2000-01'})
    assert compare(first,second)['reason']=='period_mismatch'
