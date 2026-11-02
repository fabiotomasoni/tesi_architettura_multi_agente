"""Controlla il registro delle prove; non importa runtime né esegue procedure."""
import ast
import json
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
CELLS={'S+P':{'organization':'single','minimization':'active'},
       'M+P':{'organization':'multi','minimization':'active'},
       'S-P':{'organization':'single','minimization':'disabled'},
       'M-P':{'organization':'multi','minimization':'disabled'}}
REQUIREMENTS={
    'V-01':{'RF-01','RF-02','RF-04','RF-05','RF-06','RF-07','RF-08','RF-10','RNF-06','RNF-07'},
    'V-02':{'RF-03','RNF-01','RNF-02'},'V-03':{'RF-01','RF-02','RF-09'},
    'V-04':{'RF-09','RNF-04'},'V-05':{'RF-05','RNF-03'},
    'V-06':{'RF-04','RF-05','RNF-05'},'V-07':{'RF-03','RF-08','RNF-08'},
    'V-08':{'RF-06','RF-08','RF-09','RNF-07'},
    'V-09':{'RF-02','RF-07','RF-08','RNF-07'},'V-10':{'RF-04','RNF-03'},
}
CYCLES={'V02-FINALIZATION','V02-PAYLOADS','V03-INPUTS','V04-SOURCES','V05-HOSTILE',
        'V06-SUBSTITUTION','V07-UTILITY_LOSS','V08-PROVENANCE','V09-COMPARISONS','V10-CARDS'}
GATED={'V02-PAYLOADS','V05-HOSTILE','V10-CARDS'}


def reference_exists(root, reference):
    path,_,symbol=reference.partition('::')
    relative=PurePosixPath(path)
    if relative.is_absolute() or '..' in relative.parts:
        return False
    target=root/path
    if not target.is_file():return False
    if not symbol:return True
    return any(isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==symbol
               for node in ast.walk(ast.parse(target.read_text())))


def verify(registry, protocol, annotations, *, root=ROOT):
    checks={
        'draft_definition_only':registry['registry_version']=='v01-v10-registry-draft-v1'
            and registry['status']=='defined_pending_implementation_and_freeze',
        'protocol_points_to_this_registry':protocol.get('test_registry')=={
            'path':'evaluation/test_registry.json','version':registry['registry_version'],
            'status':registry['status'],'authorizes_execution':False},
        'four_cells':registry['design']['cells']==CELLS,
        'ten_repetitions':registry['design']['repetitions_per_cell']==registry['design']['additional_cycle_repetitions_per_cell']==protocol['design']['repetitions']==10,
        'base_1000_not_all_verifications':registry['design']['base_case_count']==protocol['design']['base_pdf_cases']==25
            and registry['design']['base_executions']==protocol['design']['base_executions']==1000
            and protocol['design']['includes_all_V01_V10'] is False,
        'physical_totals_not_invented':registry['design']['final_physical_session_total'] is None
            and registry['design']['final_report_rating_total'] is None,
        'local_fixed_sources':registry['design']['nominal_sources']=='fixed_local_fixtures'
            and registry['design']['external_network_in_comparison'] is False,
        's04_still_not_authorized':registry['scope_decisions']['s04_authorized'] is False
            and protocol['security_stage']=='S04_not_authorized'
            and 'approve_remaining_S04_scope' in protocol['freeze_blockers'],
        'final_campaign_still_not_authorized':registry['scope_decisions']['final_campaign_authorized'] is False
            and protocol['final_campaign_started'] is False and protocol['approved_by'] is None and protocol['frozen_at'] is None,
        'remaining_instance_gate_not_removed': 'complete_controlled_instances_for_V01_V10' in protocol['freeze_blockers'],
        'new_runtime_version_and_pilot_required':registry['design']['current_runtime_protocol']==protocol['runtime_protocol']
            and registry['design']['runtime_after_agent_extension']=='new_version_required_not_yet_defined',
    }
    shared=registry['scope_decisions']['shared_observation']
    checks['confirmed_real_agent_extension_not_component_substitution']=(shared['status']=='user_confirmed_scope_only'
        and all(shared[k] is True for k in ('agent_extension_required','end_to_end_required',
              'both_agents_read_same_public_reference_via_mcp','document_values_stay_local',
              'tests_use_declared_simulated_reference','gateway_verifies_each_source_receipt',
              'requires_new_runtime_protocol_and_four_cell_pilot'))
        and shared['implementation_status']=='pending')
    reference=shared['reference_definition']
    checks['one_existing_official_public_reference']=(shared['exact_quantity_and_fixture_receipts']=='ecb_aggregate_aar_nder_and_existing_recorded_snapshot_selected'
        and reference['source_id']=='ecb-mir-it-house-purchase-v1'
        and reference['series_key']=='MIR.M.IT.B.A2C.A.R.A.2250.EUR.N'
        and reference['source_portal_url']=='https://data.ecb.europa.eu/data/datasets/MIR/MIR.M.IT.B.A2C.A.R.A.2250.EUR.N'
        and reference['quantity']=='aggregate_aar_nder' and reference['product']=='Italy_new_house_purchase_loans'
        and reference['unit']=='percent_per_year' and reference['period_granularity']=='month'
        and reference['value_origin']=='OBS_VALUE_in_verified_source_csv_not_model_output'
        and reference['evidence_contract']=='gateway.ecb_source.EcbRateEvidence'
        and reference['observation_contract']=='gateway.comparisons.Observation'
        and reference['offline_mode']=='recorded_official_response_replay_not_new_web_retrieval'
        and reference['status']=='contract_defined_agent_integration_pending')
    checks['existing_reference_contract_and_snapshot']=(reference_exists(root,reference['observation_adapter'])
        and reference_exists(root,reference['offline_fixture']))
    cases={c['case_id']:c for c in annotations['cases']}
    cohorts=registry['cohorts']
    checks['cohort_all_base']=set(cohorts['all_base'])==set(cases)=={f'C{i:03}' for i in range(1,26)}
    partition=[c for name in ('complete','missing_mortgage','missing_tax','ambiguous_rate') for c in cohorts[name]]
    checks['cohort_partition']=len(partition)==25 and set(partition)==set(cases)
    for name,values in cohorts.items():
        checks['cohort/'+name+'/known_unique_cases']=len(values)==len(set(values)) and set(values)<=set(cases)
    checks['complete_matches_reference']=set(cohorts['complete'])=={cid for cid,c in cases.items() if all(s=='completed' for s in c['expected_activities'].values())}
    checks['mortgage_eligible_matches_reference']=set(cohorts['mortgage_eligible'])=={cid for cid,c in cases.items() if c['expected_activities']['S-01']=='completed'}
    for cohort,field,status in [('missing_mortgage','remaining_principal','missing'),('missing_tax','annual_interest','missing'),('ambiguous_rate','annual_rate','ambiguous')]:
        checks[cohort+'/matches_reference']=set(cohorts[cohort])=={cid for cid,c in cases.items() if c['facts'][field]['status']==status}
    families=registry['families']
    checks['ten_unique_families']=len(families)==10 and {g['id'] for g in families}==set(REQUIREMENTS)
    cycle_ids=[]
    allowed_inputs=set(cases)|{'planned_scan_pdf','planned_encrypted_pdf','planned_corrupt_pdf',
                              'C001_mutuo_plus_planned_corrupt_pdf','C006_S-01_only'}
    for family in families:
        fid=family['id']
        checks[fid+'/requirements_match_thesis']=set(family['thesis_requirements'])==REQUIREMENTS.get(fid)
        checks[fid+'/final_not_claimed']=family['final_campaign_complete'] is False
        for index,coverage in enumerate(family['base_coverage']):
            checks[fid+f'/base/{index}']=coverage['cohort'] in cohorts and bool(coverage['assertions'])
        for reference in family['existing_evidence_references']:
            checks[fid+'/'+reference]=reference_exists(root,reference)
        for cycle in family['additional_cycles']:
            cid=cycle['id'];cycle_ids.append(cid)
            checks[cid+'/correct_family']=cid.startswith(fid.replace('-','')+'-')
            checks[cid+'/no_false_readiness']=cycle['implementation_status']=='pending' and cycle['final_completed_repetitions']==0 and cycle['final_command'] is None
            checks[cid+'/pipeline_required']=cycle['execution_level']=='end_to_end_required'
            checks[cid+'/security_gate']=cycle['s04_required']==(cid in GATED)
            checks[cid+'/controls_and_pending_work']=bool(cycle['positive_controls']) and bool(cycle['remaining_work'])
            variants=cycle['variants']
            checks[cid+'/unique_variants']=bool(variants) and len({v['id'] for v in variants})==len(variants)
            for variant in variants:
                checks[cid+'/'+variant['id']+'/defined']=bool(variant['expected']) and variant['inputs'] in allowed_inputs
    checks['ten_unique_additional_cycles']=len(cycle_ids)==10 and set(cycle_ids)==CYCLES
    artifacts=registry['planned_artifacts']
    checks['negative_artifacts_not_claimed_built']=(len(artifacts)==3
        and {a['id'] for a in artifacts}=={'planned_scan_pdf','planned_encrypted_pdf','planned_corrupt_pdf'}
        and all(a['synthetic_only'] is True and a['status']=='not_built' and a['path'] is None
                and a['sha256'] is None and a['reviewed'] is False for a in artifacts))
    required_rules={'base_reuse','cycle_variants','session_independence','counting','reuse_controls',
                    'unknowns','privacy','rejected_inputs','fault_profiles','source_timeout',
                    'untrusted_outputs','human_review','report_absence','no_run_authority'}
    checks['common_rules_present']=required_rules<=set(registry['common_rules']) and all(registry['common_rules'][key] for key in required_rules)
    return checks


def main():
    try:
        registry=json.loads((ROOT/'evaluation/test_registry.json').read_text())
        protocol=json.loads((ROOT/'evaluation/protocol.json').read_text())
        annotations=json.loads((ROOT/'evaluation/annotations.json').read_text())
        checks=verify(registry,protocol,annotations)
    except (ValueError,KeyError,TypeError,OSError):
        raise SystemExit('Registro non valido: struttura o riferimenti da correggere. Nessuna prova eseguita.') from None
    failed=[key for key,value in checks.items() if not value]
    print('Controlli:',len(checks));print('Problemi:',len(failed))
    for key in failed:print(key)
    print('Famiglie V:',len(registry['families']))
    print('Cicli aggiuntivi:',sum(len(g['additional_cycles']) for g in registry['families']))
    print('Pronto per campagna finale: False')
    print('S04 autorizzato: False')
    print('Procedure eseguite: 0')
    raise SystemExit(1 if failed else 0)


if __name__=='__main__':main()
