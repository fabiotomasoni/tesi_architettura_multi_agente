"""Quattro assetti logici isolati in processi; nessuna misura di qualità LLM."""
import json,os,subprocess,sys
import pytest
PROFILES=('nominal','source_timeout','source_malformed','both_unavailable','missing_market',
          'both_missing','hostile_result','metadata','conflict_agents','conflict_document',
          'equivalent_units','different_period','different_product','unfaithful_result',
          'payload_identifier','payload_financial','card_identity','card_endpoint','card_capabilities')
@pytest.mark.parametrize('organization',['single','multi'])
@pytest.mark.parametrize('policy',['active','disabled'])
@pytest.mark.parametrize('profile',PROFILES)
def test_controlled_pipeline_in_four_logical_cells(organization,policy,profile):
    env={**os.environ,'TESI_RUNTIME':'local','TESI_EXPERIMENT':organization,'TESI_MINIMIZATION':policy,
        'TESI_SHARED_REFERENCE':'1','TESI_VERIFICATION_PROFILE':profile,'TESI_MARKET_SOURCE':'simulated',
        'TESI_TAX_SOURCE':'simulated','TESI_MCP_PROFILE':'nominal','TESI_MARKET_TOOL_IMPLEMENTATION':'standard'}
    r=subprocess.run([sys.executable,'-m','tests.block2_worker'],env=env,capture_output=True,text=True,timeout=150)
    assert r.returncode==0,r.stdout[-1500:]+r.stderr[-4500:]
    last=json.loads(r.stdout.strip().splitlines()[-1]);assert last['passed'] and last['cleanup']
