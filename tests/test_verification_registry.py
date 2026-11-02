"""Controlli offline: una definizione coerente non autorizza prove o campagne."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.check_test_registry import verify

ROOT=Path(__file__).resolve().parents[1]


def documents():
    return tuple(json.loads((ROOT/'evaluation'/name).read_text()) for name in
                 ('test_registry.json','protocol.json','annotations.json'))


def test_registry_reuses_reference_and_keeps_agent_extension_pending():
    registry,protocol,annotations=documents()
    assert all(verify(registry,protocol,annotations).values())
    shared=registry['scope_decisions']['shared_observation']
    assert shared['end_to_end_required'] and shared['implementation_status']=='pending'
    assert registry['design']['base_executions']==1000
    assert registry['design']['final_physical_session_total'] is None
    assert not protocol['final_campaign_started']


@pytest.mark.parametrize('change',[
    'missing_family','wrong_repetitions','s04_authorized','invented_session_total',
    'ungated_card','component_only_conflict','extension_claimed_done','fabricated_pdf',
])
def test_incomplete_or_unauthorized_plan_is_not_blessed(change):
    registry,protocol,annotations=documents()
    registry=deepcopy(registry)
    if change=='missing_family':registry['families'].pop()
    if change=='wrong_repetitions':registry['design']['repetitions_per_cell']=3
    if change=='s04_authorized':registry['scope_decisions']['s04_authorized']=True
    if change=='invented_session_total':registry['design']['final_physical_session_total']=1000
    if change=='ungated_card':registry['families'][-1]['additional_cycles'][0]['s04_required']=False
    if change=='component_only_conflict':registry['families'][8]['additional_cycles'][0]['execution_level']='component_only'
    if change=='extension_claimed_done':registry['scope_decisions']['shared_observation']['implementation_status']='implemented'
    if change=='fabricated_pdf':registry['planned_artifacts'][0]['path']='not_generated.pdf'
    assert not all(verify(registry,protocol,annotations).values())


def test_cohort_must_match_reviewed_documentary_eligibility():
    registry,protocol,annotations=documents()
    # Scambiare un caso completo con uno privo del capitale mantiene 25 ID,
    # ma deve fallire il confronto con il riferimento indipendente.
    registry['cohorts']['complete'][0],registry['cohorts']['missing_mortgage'][0]='C006','C001'
    assert not all(verify(registry,protocol,annotations).values())


def test_registry_audit_is_read_only_and_does_not_start_campaign():
    files=[ROOT/'evaluation'/name for name in ('test_registry.json','protocol.json','annotations.json')]
    before=[p.read_bytes() for p in files]
    result=subprocess.run([sys.executable,'scripts/check_test_registry.py'],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'Problemi: 0' in result.stdout and 'Procedure eseguite: 0' in result.stdout
    assert 'Pronto per campagna finale: False' in result.stdout and 'S04 autorizzato: False' in result.stdout
    assert [p.read_bytes() for p in files]==before
