from copy import deepcopy
import json
from pathlib import Path
import pytest
from gateway.comparisons import Observation,compare,evaluate
from gateway.report import build_report
from gateway.models import SessionInput


def observation(**updates):
    data=dict(observation_id='doc',quantity='contract_annual_rate',product='mortgage-1',period='2025-12-31',value='3.10',unit='percent_per_year',source_kind='document',source_ref='doc-test#page/1',verified=True)
    data.update(updates)
    return Observation(**data)


@pytest.mark.parametrize('kind',['document','agent'])
def test_conflict_retains_both_sources_and_values(kind):
    a=observation();b=observation(observation_id='other',value='4.25',source_kind=kind,source_ref='other-source')
    before=a.model_dump(),b.model_dump()
    result=compare(a,b)
    assert result['status']=='conflict'
    assert result['left']==before[0] and result['right']==before[1]
    assert (a.model_dump(),b.model_dump())==before


def test_agent_agent_conflict():
    assert compare(observation(source_kind='agent'),observation(observation_id='b',value='4.25',source_kind='agent'))['status']=='conflict'


@pytest.mark.parametrize('updates,reason',[
 ({'quantity':'payment_amount','unit':'EUR'},'quantity_mismatch'),
 ({'quantity':'market_annual_rate'},'quantity_mismatch'),
 ({'product':'another'},'product_mismatch'),
 ({'period':'2024-12-31'},'period_mismatch'),
 ({'unit':'percent_per_month'},'unsupported_unit'),
 ({'verified':False},'unverified_observation'),
 ({'value':'NaN'},'invalid_numeric_value'),
])
def test_not_comparable(updates,reason):
    result=compare(observation(),observation(observation_id='b',**updates))
    assert result['status']=='not_comparable' and result['reason']==reason


def test_convertible_units_and_explicit_tolerance():
    assert compare(observation(),observation(observation_id='b',value='310',unit='basis_points_per_year'))['status']=='consistent'
    assert compare(observation(),observation(observation_id='b',value='0.031',unit='fraction_per_year'))['status']=='consistent'
    b=observation(observation_id='b',value='3.11')
    assert compare(observation(),b)['status']=='conflict'
    assert compare(observation(),b,{'contract_annual_rate':'0.01'})['status']=='consistent'


def test_money_duration_conversion():
    assert compare(observation(quantity='payment_amount',value='100',unit='EUR'),observation(observation_id='b',quantity='payment_amount',value='10000',unit='EUR_cent'))['status']=='consistent'
    assert compare(observation(quantity='remaining_duration',value='12',unit='month'),observation(observation_id='b',quantity='remaining_duration',value='1',unit='year'))['status']=='consistent'


def test_report_exposes_conflict_without_overwriting_profile():
    profile=SessionInput.model_validate(json.loads(Path('examples/session_complete.json').read_text())).profile
    original=profile.annual_rate.value
    extra=observation(observation_id='agent',product='uploaded_mortgage',period=profile.annual_rate.period.isoformat(),value='99',source_kind='agent',source_ref='test-agent')
    report=build_report(profile,['S-01'],{'S-01':{'status':'blocked','error_code':'test'}},'blocked',comparison_observations=[extra])
    assert report['analysis_status']=='unresolved_conflict'
    assert report['consistency']['unresolved_conflicts']==1
    assert profile.annual_rate.value==original
