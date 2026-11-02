"""Ricevute del riferimento pubblico comune, distinte da TAN e regole fiscali."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Literal
from .models import Contract
from .comparisons import Observation
from .ecb_source import EcbRateEvidence,verify_ecb,parse_csv

VERSION='shared-reference-1'
DESTINATION='fixture://shared-public-reference-v1'
MODULE='services.reference_mcp'
TOOL='lookup_reference'

class ReferenceReceipt(Contract):
    version: Literal['shared-reference-1']='shared-reference-1'
    fixture_profile: Literal['nominal','conflict_agents','conflict_document','equivalent_units','different_period','different_product']='nominal'
    origin: Literal['recorded_official_response_replay','simulated_counterfactual']
    source_id: str
    quantity: str
    product: str
    period: str
    value: str
    unit: str
    recorded_evidence: dict | None=None


def expected(scenario,profile='nominal'):
    raw=json.loads((Path(__file__).parent/'fixtures/ecb_reference.json').read_text())
    row=parse_csv(raw['source_csv'])
    e=EcbRateEvidence(annual_rate_percent=row['OBS_VALUE'],observation_period=row['TIME_PERIOD'],
                     source_csv=raw['source_csv'],retrieved_at=raw['retrieved_at'],response_sha256=raw['response_sha256'])
    data=dict(version=VERSION,fixture_profile='nominal',origin='recorded_official_response_replay',source_id=e.source_id,
              quantity='aggregate_aar_nder',product='Italy_new_house_purchase_loans',period=e.observation_period,
              value=e.annual_rate_percent,unit=e.unit,recorded_evidence=e.model_dump(mode='json'))
    if profile in {'conflict_agents','conflict_document','equivalent_units','different_period','different_product'}:
        data.update(fixture_profile=profile,origin='simulated_counterfactual',source_id='simulated-comparison-v1',recorded_evidence=None)
        if profile=='conflict_agents':data['value']='3.00' if scenario=='S-01' else '4.00'
        if profile=='conflict_document':
            data.update(quantity='contract_annual_rate',product='uploaded_mortgage',period='2025-12-31',value='9.00')
        if profile=='equivalent_units':data.update(value='3.00' if scenario=='S-01' else '300',unit='percent_per_year' if scenario=='S-01' else 'basis_points_per_year')
        if profile=='different_period':data.update(value='3.00' if scenario=='S-01' else '4.00',period='2025-01' if scenario=='S-01' else '2025-02')
        if profile=='different_product':data.update(value='3.00' if scenario=='S-01' else '4.00',product='simulated-product-A' if scenario=='S-01' else 'simulated-product-B')
    return ReferenceReceipt.model_validate(data)


def verify(raw,scenario,profile=None):
    if not isinstance(raw,dict) or set(raw)!=set(ReferenceReceipt.model_fields):raise ValueError('Ricevuta del riferimento incompleta')
    receipt=ReferenceReceipt.model_validate(raw)
    if receipt!=expected(scenario,receipt.fixture_profile if profile is None else profile):raise ValueError('Riferimento difforme dalla ricevuta configurata')
    if receipt.recorded_evidence is not None:verify_ecb(receipt.recorded_evidence)
    digest=hashlib.sha256(json.dumps(receipt.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return receipt,digest


def observation(receipt,scenario):
    return Observation(observation_id='shared-reference-'+scenario,quantity=receipt.quantity,product=receipt.product,
        period=receipt.period,value=receipt.value,unit=receipt.unit,source_kind='agent',
        source_ref=receipt.source_id+'#'+receipt.period+'/'+scenario,verified=True)
