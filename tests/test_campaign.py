"""Validità della valutazione: niente voti inventati, drift o repliche nascoste."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import asyncio,csv,json
import httpx,pytest
from scripts.campaign_support import (ROOT,Collector,plan,read,write_new,digest,verify_bundle,check_approval,describe,blind,source_files)
from scripts.prepare_campaign import prepare
from scripts.review_campaign import export_review,read_ratings,summarize,interval_union
from tests.test_report_document import report


@pytest.fixture
def bundle(tmp_path):
    path=tmp_path/'campaign';prepare(path,{'scope':'test_snapshot_not_actual_machine'});return path


def test_schedule_covers_ten_independent_repetitions_four_cells_and_all_cases():
    p=plan();assert len(p['blocks'])==40 and len(p['controlled_variants'])==29
    assert p['counts']=={'base_sessions':1000,'controlled_created_sessions':2400,'expected_created_sessions':3400,'rejected_upload_attempts':120,'expected_upload_attempts':3520,'expected_delivered_reports':3200}
    positions={cell:Counter() for cell in ('single-active','single-disabled','multi-active','multi-disabled')}
    for rep in range(1,11):
        blocks=[b for b in p['blocks'] if b['repetition']==rep]
        assert len(blocks)==4 and len({tuple(b['cases']) for b in blocks})==1
        assert set(blocks[0]['cases'])=={f'C{i:03}' for i in range(1,26)}
        for block in blocks:positions[block['cell']][block['position']]+=1
    assert all(max(c.values())-min(c.values())<=1 for c in positions.values())
    assert plan()==p and plan(pilot=True)['counts']['base_sessions']==20


def test_preparation_does_not_approve_or_start_a_campaign(bundle):
    assert not verify_bundle(bundle)
    assert not (bundle/'approval.json').exists() and not (bundle/'final').exists()
    with pytest.raises(ValueError):check_approval(bundle)
    with pytest.raises(ValueError):prepare(bundle,{})
    assert all(not k.startswith(('.local/','runs/')) and not Path(k).is_absolute() for k in source_files())


@pytest.mark.parametrize('artifact',['plan.json','pilot_plan.json','protocol.json','registry.json','annotations.json'])
def test_changed_frozen_artifact_is_detected(bundle,artifact):
    value=read(bundle/artifact);value['changed']=True;(bundle/artifact).write_text(json.dumps(value))
    assert artifact+'_changed' in verify_bundle(bundle)


def test_environment_and_approval_bound_to_exact_manifest(bundle):
    assert 'environment_or_model_drift' in verify_bundle(bundle,environment={'model':'changed'})
    approval={'manifest_sha256':digest(read(bundle/'manifest.json')),'approved_by':'user','scope':'frozen_protocol_and_final_execution','final_campaign_authorized':True}
    write_new(bundle/'approval.json',approval);check_approval(bundle)
    value=read(bundle/'manifest.json');value['environment']={};(bundle/'manifest.json').write_text(json.dumps(value))
    with pytest.raises(ValueError):check_approval(bundle)


def test_no_docker_execution_without_separate_approval(bundle,monkeypatch):
    import scripts.run_campaign as runner
    monkeypatch.setattr(runner,'environment',lambda:read(bundle/'manifest.json')['environment'])
    def forbidden(*a,**kw):pytest.fail('Docker reached before approval')
    monkeypatch.setattr(runner,'call',forbidden)
    with pytest.raises(ValueError):runner.run(bundle)


def test_missing_observations_are_not_zero_and_variance_is_sample_variance():
    assert describe([1,None,3])=={'n':2,'missing':1,'mean':2,'sample_variance':2}
    assert describe([None])=={'n':0,'missing':1,'mean':None,'sample_variance':None}
    assert describe([2])['sample_variance'] is None
    assert interval_union([{'start_ms':0,'duration_ms':10},{'start_ms':5,'duration_ms':10}])==15
    assert interval_union([{'start_ms':0,'duration_ms':None}]) is None


def observed(folder,variant='nominal',n=1):
    collector=Collector(folder,{'id':'r01-single-active','cell':'single-active','repetition':1},'controlled')
    collector.context={'case':'C001','variant':variant}
    for i in range(n):
        sid=str(i)
        collector.capture('POST','/sessions/pdf',201,{'session_id':sid},'trace-'+sid)
        collector.capture('POST','/sessions/'+sid+'/analysis',200,{'status':'completed','report':report(),'session_closed':True})
        collector.capture('DELETE','/sessions/'+sid,404,{})
    return collector


def test_failure_to_deliver_is_not_a_report_for_human_rating(tmp_path):
    collector=observed(tmp_path,'delivery_relay',3);rows=collector.finish(procedure_passed=True)
    assert len(rows)==3 and sum(r['report_delivered'] for r in rows)==2
    assert rows[1]['role']=='fault' and rows[1]['report_path']
    assert rows[1]['absence_reason']=='controlled_delivery_fault'
    assert all(r['cleanup_verified'] for r in rows)


def test_blinding_preserves_all_financial_values_quotes_and_selected_content():
    original=report();before=deepcopy(original);result=blind(original)
    assert original==before and 'policy_version' not in result
    for key in ('document_data','faithful_summaries','mortgage_contract_analysis','tax_application','limits','consistency'):
        assert result[key]==original[key]


@pytest.fixture
def review(tmp_path):
    collector=observed(tmp_path,n=2);rows=collector.finish(procedure_passed=True)
    write_new(tmp_path/'private/blocks/r01.json',{'rows':rows})
    assert export_review(tmp_path)==2
    return tmp_path


def fill(path):
    with path.open(newline='',encoding='utf-8') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    for row in rows:row.update(correctness='2',coverage='2',provenance='2',limits='2',critical_error='no')
    with path.open('w',newline='',encoding='utf-8') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return fields,rows


def test_all_reports_kept_even_if_identical_and_scores_start_empty(review):
    with (review/'public/ratings.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==2 and len({r['evaluation_id'] for r in rows})==2
    assert all(r['correctness']==r['critical_error']=='' for r in rows)
    with pytest.raises(ValueError):read_ratings(review,review/'public/ratings.csv')
    fill(review/'public/ratings.csv');scores=read_ratings(review,review/'public/ratings.csv')
    assert len(scores)==2 and all(s['total']==8 for s in scores.values())
    with pytest.raises(ValueError):export_review(review)


@pytest.mark.parametrize('change',['unknown','duplicate','missing','wrong_hash','wrong_case','blank','out_of_range','html_modified','json_modified'])
def test_human_registry_rejects_missing_tampered_or_invalid_scores(review,change):
    path=review/'public/ratings.csv';fields,rows=fill(path)
    if change=='unknown':rows[0]['evaluation_id']='E-unknown'
    if change=='duplicate':rows.append(rows[0])
    if change=='missing':rows.pop()
    if change=='wrong_hash':rows[0]['report_sha256']='wrong'
    if change=='wrong_case':rows[0]['case_id']='C025'
    if change=='blank':rows[0]['coverage']=''
    if change=='out_of_range':rows[0]['coverage']='3'
    if change=='html_modified':next((review/'public/reports').glob('*.html')).write_text('Different text')
    if change=='json_modified':next((review/'public/reports').glob('*.json')).write_text('{}')
    with path.open('w',newline='') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError):read_ratings(review,path)


def test_summary_separates_controlled_and_actual_usage_and_keeps_unknown_costs():
    rows=[{'run_id':f'r{rep}-base-001','kind':'base','cell':'single-active','case':'C001','variant':'nominal','repetition':rep,'status':'completed','report_delivered':True,'total_ms':ms,'cleanup_verified':True,'passed':True,'trace':{'summary':{'prompt_tokens':tokens}},'utility':{'S-01':{'ratio':1},'S-02':{'ratio':None}}} for rep,ms,tokens in [(1,10,5),(2,20,None)]]
    result=summarize(rows);g=result['groups'][0]
    assert g['metrics']['total_ms']['sample_variance']==50 and g['metrics']['prompt_tokens']['missing']==1
    assert g['quality']['mean'] is None and result['individual_quality_thresholds_satisfied'] is None
    assert g['utility']['S-02']['mean'] is None and g['observed_money_EUR'] is None
    assert result['observed_unauthorized_transmissions'] is None and result['required_unauthorized_transmissions']==0
    assert result['quality_rated']==0


def test_async_collector_records_real_http_reply_and_trace_without_request_contents(tmp_path):
    collector=Collector(tmp_path,{'id':'r01-single-active','cell':'single-active','repetition':1},'base')
    def mock(request):
        path=request.url.path
        if path=='/sessions/pdf':return httpx.Response(201,json={'session_id':'s'},headers={'x-trace-id':'t'})
        if path=='/sessions/s/analysis':return httpx.Response(200,json={'status':'completed','report':report()},headers={'x-trace-id':'t'})
        if path=='/traces/t':return httpx.Response(200,json={'profile_closed':True,'summary':{'prompt_tokens':7}})
        return httpx.Response(404,json={})
    async def run():
        factory=collector.async_factory(lambda:{'case':'C001','variant':'nominal'})
        async with factory(base_url='http://127.0.0.1:8080',transport=httpx.MockTransport(mock)) as client:
            await client.post('/sessions/pdf',content=b'RAW_PRIVATE_DOCUMENT')
            await client.post('/sessions/s/analysis',headers={'Authorization':'PRIVATE_TOKEN'})
    asyncio.run(run());rows=collector.finish(procedure_passed=True)
    assert rows[0]['report_delivered'] and rows[0]['trace']['summary']['prompt_tokens']==7
    assert 'RAW_PRIVATE_DOCUMENT' not in json.dumps(rows) and 'PRIVATE_TOKEN' not in json.dumps(rows)


@pytest.mark.parametrize('case',['C001','C006','C011','C016','C024'])
def test_financial_report_matches_independent_reviewed_reference(case):
    from scripts.campaign_support import reference_checks
    annotation=next(c for c in read(ROOT/'evaluation/annotations.json')['cases'] if c['case_id']==case)
    assert all(reference_checks(report(case),annotation).values())
    if case=='C001':
        changed=report(case);changed['document_data'][0]['facts']['remaining_principal']['value']='1'
        assert not reference_checks(changed,annotation)['reference_fact/remaining_principal']


def test_removing_a_delivered_report_from_private_mapping_does_not_complete_rating(review):
    fill(review/'public/ratings.csv')
    path=review/'private/review_mapping.json';mapping=read(path);mapping['entries'].pop();path.write_text(json.dumps(mapping))
    with pytest.raises(ValueError):read_ratings(review,review/'public/ratings.csv')


def test_summary_reports_paired_organization_effect_and_interaction():
    rows=[]
    for cell,time in [('single-active',10),('multi-active',15),('single-disabled',20),('multi-disabled',22)]:
        rows.append({'run_id':cell+'-base-001','kind':'base','cell':cell,'case':'C001','variant':'nominal','repetition':1,'status':'completed','report_delivered':True,'total_ms':time})
    result=summarize(rows)
    effect=next(e for e in result['organization_contrasts'] if e['metric']=='total_ms')
    interaction=next(e for e in result['interaction_contrasts'] if e['metric']=='total_ms')
    assert effect['multi_minus_single']['active']['mean']==5
    assert effect['multi_minus_single']['disabled']['mean']==2
    assert interaction['organization_effect_with_policy_minus_without_policy']['mean']==3
    with pytest.raises(ValueError):summarize(rows+[rows[0]])


def test_completed_evidence_hashes_detect_changed_or_deleted_report(bundle):
    from scripts.campaign_support import result_hashes,verify_results
    schedule=read(bundle/'pilot_plan.json');folder=bundle/'pilot'
    for block in schedule['blocks']:write_new(folder/'private/blocks'/(block['id']+'.json'),{'block':block,'rows':[]})
    write_new(folder/'completion.json',{'blocks':4,'manifest_sha256':digest(read(bundle/'manifest.json')),'private_sha256':result_hashes(folder),'passed':True})
    assert verify_results(bundle,pilot=True)==[]
    path=next((folder/'private/blocks').glob('*.json'));path.write_text('{}')
    assert 'result_artifact_drift' in verify_results(bundle,pilot=True)


def test_lost_upload_reply_is_retained_as_unknown_and_never_claimed_clean(tmp_path):
    collector=Collector(tmp_path,{'id':'r01-single-active','cell':'single-active','repetition':1},'base')
    def lost(request):raise httpx.ConnectError('controlled transport error')
    async def run():
        factory=collector.async_factory(lambda:{'case':'C006','variant':'nominal'})
        async with factory(base_url='http://127.0.0.1:8080',transport=httpx.MockTransport(lost)) as client:
            with pytest.raises(httpx.ConnectError):await client.post('/sessions/pdf')
    asyncio.run(run());rows=collector.finish(procedure_passed=False)
    assert len(rows)==1 and rows[0]['case']=='C006'
    assert rows[0]['profile_created'] is None and rows[0]['cleanup_verified'] is False
    assert rows[0]['report_delivered'] is False


def test_unavailable_host_memory_is_unknown_not_zero_and_does_not_fake_measurement(monkeypatch):
    import scripts.prepare_campaign as preparation
    monkeypatch.setattr(preparation.platform,'system',lambda:'Darwin')
    def unavailable(*args):raise ValueError('Controlled optional metadata unavailability')
    monkeypatch.setattr(preparation,'command',unavailable)
    assert preparation.memory_capacity() is None


@pytest.mark.parametrize('status',[{}, {'models':[{'name':'loaded'}]}])
def test_missing_or_warm_initial_state_is_rejected_before_measuring(status):
    from scripts.campaign_support import require_cold_models
    with pytest.raises(ValueError):require_cold_models(status)
    require_cold_models({'models':[]})


def test_actual_model_usage_requires_dispatch_receipts_not_only_model_name_or_tokens():
    from scripts.campaign_support import actual_model_receipts
    span={'phase':'bridge_wait','outcome':'completed','metrics':{'execution_controlled_fixture':0,'host_http_dispatch_attempts':1,'host_http_responses_observed':1}}
    assert actual_model_receipts({'spans':[span]},1)
    fake=deepcopy(span);fake['metrics']['execution_controlled_fixture']=1
    assert not actual_model_receipts({'spans':[fake]},1)
    assert not actual_model_receipts({'spans':[]},1)
    unknown=deepcopy(span);unknown['metrics']['host_http_responses_observed']=None
    assert not actual_model_receipts({'spans':[unknown]},1)
