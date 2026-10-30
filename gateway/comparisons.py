"""Confronti locali RF-07: semantica prima dei numeri, nessuna scelta di vincitori."""
from decimal import Decimal, InvalidOperation
from itertools import combinations
from typing import Literal
from pydantic import Field
from .models import Contract
from .agent_contracts import RateEvidence

CATALOG_VERSION='0.1.0'
# Tolleranza iniziale esatta, nessuna soglia sperimentale dedotta dai risultati.
CATALOG={
    'contract_annual_rate':('percent_per_year', {'percent_per_year':'1','fraction_per_year':'100','basis_points_per_year':'0.01'}, '0'),
    'market_annual_rate':('percent_per_year', {'percent_per_year':'1','fraction_per_year':'100','basis_points_per_year':'0.01'}, '0'),
    'remaining_principal':('EUR', {'EUR':'1','EUR_cent':'0.01'}, '0'),
    'payment_amount':('EUR', {'EUR':'1','EUR_cent':'0.01'}, '0'),
    'annual_interest':('EUR', {'EUR':'1','EUR_cent':'0.01'}, '0'),
    'remaining_duration':('month', {'month':'1','year':'12'}, '0'),
}


class Observation(Contract):
    observation_id: str = Field(min_length=1,max_length=100)
    quantity: str = Field(min_length=1,max_length=100)
    product: str = Field(min_length=1,max_length=100)
    period: str = Field(min_length=1,max_length=100)
    value: str
    unit: str
    source_kind: Literal['document','agent']
    source_ref: str = Field(min_length=1,max_length=200)
    verified: bool = False


def compare(left: Observation, right: Observation, tolerances=None):
    result={'left':left.model_dump(),'right':right.model_dump(),'status':'not_comparable','reason':None}
    if not left.verified or not right.verified:result['reason']='unverified_observation';return result
    for key in ['quantity','product','period']:
        if getattr(left,key)!=getattr(right,key):result['reason']=key+'_mismatch';return result
    rule=CATALOG.get(left.quantity)
    if not rule:result['reason']='unknown_quantity';return result
    unit,factors,default=rule
    if left.unit not in factors or right.unit not in factors:result['reason']='unsupported_unit';return result
    try:
        a=Decimal(left.value)*Decimal(factors[left.unit]);b=Decimal(right.value)*Decimal(factors[right.unit])
        tolerance=Decimal((tolerances or {}).get(left.quantity,default))
        if not all(x.is_finite() for x in [a,b,tolerance]) or tolerance<0:raise ValueError()
    except (ValueError,InvalidOperation):result['reason']='invalid_numeric_value';return result
    delta=abs(a-b)
    result.update(status='consistent' if delta<=tolerance else 'conflict',reason='within_tolerance' if delta<=tolerance else 'unresolved_difference',
                  normalized={'left':str(a),'right':str(b),'unit':unit,'absolute_difference':str(delta),'tolerance':str(tolerance)})
    return result


def evaluate(observations, tolerances=None):
    observations=[Observation.model_validate(o) for o in observations]
    if len({o.observation_id for o in observations})!=len(observations):raise ValueError('ID osservazioni duplicati')
    pairs=[compare(a,b,tolerances) for a,b in combinations(observations,2)]
    return {'catalog_version':CATALOG_VERSION,'default_tolerance':'0','comparisons':pairs,
            'unresolved_conflicts':sum(p['status']=='conflict' for p in pairs),
            'comparable_pairs':sum(p['status']!='not_comparable' for p in pairs),
            'decision':'Nessun valore viene sovrascritto o selezionato automaticamente.'}


def report_observations(profile, sources):
    result=[]
    fact=profile.annual_rate
    if fact and fact.status=='validated':
        result.append(Observation(observation_id='document-contract-rate',quantity='contract_annual_rate',product='uploaded_mortgage',period=fact.period.isoformat(),value=str(fact.value),unit=fact.unit,source_kind='document',source_ref=f'{fact.source.document_id}#page/{fact.source.page}',verified=True))
    for source in sources:
        if source['scenario']=='S-01':
            evidence=RateEvidence.model_validate(source['evidence']).model_dump(mode='json')
            result.append(Observation(observation_id='agent-market-rate',quantity='market_annual_rate',product='market_fixture',period=evidence['reference_date'],value=evidence['annual_rate_percent'],unit=evidence['unit'],source_kind='agent',source_ref=evidence['source_id']+'#annual_rate_percent',verified=True))
    return result
