"""Pilota controllato delle quattro celle Docker; non campagna o giudizio umano.

Riconfigura il progetto locale tesi-s03 e ripristina la demo base alla fine.
Il ponte ordinario deve essere fermo. Modelli controllati per le prove funzionali;
--live-pilot ripete separatamente i cinque casi con Ollama realmente in esecuzione.
"""
import argparse,asyncio,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CELLS=('single-active','single-disabled','multi-active','multi-disabled')
PROFILES=('nominal','source_timeout','source_malformed','both_unavailable','missing_market','both_missing',
          'hostile_result','metadata','conflict_agents','conflict_document','equivalent_units','different_period',
          'different_product','utility_loss','payload_identifier','payload_financial','card_identity','card_endpoint','card_capabilities')

def command(args,env=None,timeout=180):
    result=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('Comando di verifica non riuscito; nessun successo attribuito.')
    return result.stdout

async def cell_run(args):
    import httpx
    from check_finalization import DockerGateway,ControlledDemo,check_delivery,check_crash
    from check_cancellation import check as cancellation
    from check_report_provenance import verify as provenance
    from check_mortgage import verify as mortgage
    from check_tax_application import verify as tax
    from check_tax_review import verify as tax_review
    from trace_export import record_trace
    from run_ollama_bridge import validate_payload
    from gateway import runtime
    from gateway.shared_reference import verify as verify_reference
    from check_substitution import normalized,digest
    org,policy=args.cell.split('-')
    controller=DockerGateway()
    files=['compose.isolated.yaml','compose.experiment-'+org+'.yaml']
    if policy=='disabled':files.append('compose.experiment-unminimized.yaml')
    files.append('compose.verification.yaml')
    base=[controller.docker,'compose']
    for file in files:base+=['-f',file]
    base+=['--profile','verification']
    controller.compose=base
    identity=json.loads((ROOT/('.local/baseline/bridge.json' if org=='single' else '.local/s03/bridge.json')).read_text())
    headers={'x-tesi-service-key':identity['keys']['bridge']}
    rows=[];args._rows=rows
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8080',timeout=150,trust_env=False) as client:
        async def configure(profile='nominal',implementation='standard',initial=False):
            args._phase=profile+'/'+implementation
            env={**os.environ,'TESI_VERIFICATION_PROFILE':profile}
            cmd=base+(['-f','compose.substitution.yaml'] if implementation=='equivalent' else [])
            cmd+=['up','-d','--no-build']+([] if initial else ['--no-deps','gateway'])
            await asyncio.to_thread(command,cmd,env)
            for _ in range(120):
                try:
                    h=(await client.get('/health',timeout=2)).json()
                    if (h.get('experiment'),h.get('minimization'),h.get('verification_profile'),h.get('market_tool_implementation'),h.get('shared_reference'))==(org,policy,profile,implementation,True):
                        if initial:
                            for service,port in [('markets',8001)]+([('tax',8002)] if org=='multi' else []):
                                code='import socket; s=socket.create_connection(("127.0.0.1",'+str(port)+'),timeout=2);s.close()'
                                await asyncio.to_thread(command,base+['exec','-T',service,'python','-c',code],env)
                        return h
                except (httpx.HTTPError,ValueError,RuntimeError):pass
                await asyncio.sleep(.25)
            raise ValueError('Configurazione Docker attesa non disponibile')
        async def controlled_bridge():
            while True:
                reply=await client.get('/_bridge/poll',headers=headers,timeout=20)
                if reply.status_code==204:continue
                reply.raise_for_status();job=reply.json();payload=job['payload'];validate_payload(payload)
                data=json.loads(payload['messages'][1]['content']);fiscal='tax-selection' in payload['messages'][0]['content']
                selection={'schema_version':'tax-selection-1' if fiscal else 'market-selection-1',
                    'source_statement_ids':[s['statement_id'] for s in data['statements'] if s['kind']=='source'][:2],
                    'context_statement_id':next(s['statement_id'] for s in data['statements'] if s['kind']=='context'),'explanation':''}
                body={'message':{'content':json.dumps(selection)},'prompt_eval_count':1,'eval_count':1,'load_duration':0}
                posted=await client.post('/_bridge/result/'+job['job_id'],headers=headers,json={'body':body,'error':None,'ollama_ms':0,'source_ms':None,
                    'execution':{'kind':'controlled_fixture','dispatch_attempts':0,'responses_observed':0}})
                if posted.status_code not in {200,204,409}:posted.raise_for_status()
        async def run_case(profile='nominal',case='C001',kinds=('mutuo','interessi'),scenarios=('S-01','S-02'),extra=None):
            args._procedure={'case':case,'variant':profile}
            sid=None;identifier=None;worker=asyncio.create_task(controlled_bridge())
            try:
                files=[('files',(k+'.pdf',(ROOT/f'dataset/Documents/{case}_{k}.pdf').read_bytes(),'application/pdf')) for k in kinds]
                if extra is not None:files.append(('files',('negative.pdf',extra,'application/pdf')))
                reply=await client.post('/sessions/pdf',files=files,data={'scenarios':list(scenarios)});reply.raise_for_status()
                uploaded=reply.json();sid=uploaded['session_id'];identifier=uploaded.get('trace_id')
                utility_result=None
                if profile=='utility_loss':
                    from evaluation_support import utility
                    required=json.loads((ROOT/'evaluation/annotations.json').read_text())['cases'][0]['agent_utility_facts']['S-01']
                    view=await client.post('/sessions/'+sid+'/views',json={'scenario':'S-01','recipient':'markets'});view.raise_for_status()
                    utility_result=utility(view.json()['data'],required)
                    assert utility_result['ratio']==(.5 if policy=='active' else 1)
                reply=await client.post('/sessions/'+sid+'/analysis');reply.raise_for_status();body=reply.json();report=body['report']
                states={s:a['status'] for s,a in body['activities'].items()}
                n=int(case[1:]);expected={s:'blocked' if s=='S-01' and (6<=n<=10 or 16<=n<=20) or s=='S-02' and (11<=n<=15 or 'interessi' not in kinds) else 'completed' for s in scenarios}
                if profile=='source_timeout':expected['S-01']='failed'
                if profile=='source_malformed':expected['S-02']='failed'
                if profile in {'both_unavailable','hostile_result'}:expected={s:'failed' for s in scenarios}
                if profile in {'metadata','payload_identifier','payload_financial'}:expected={s:'blocked' for s in scenarios}
                if profile=='utility_loss' and policy=='active':expected['S-01']='blocked'
                if profile=='missing_market':expected['S-01']='unverified'
                if profile=='both_missing':expected={s:'unverified' for s in scenarios}
                if profile.startswith('card_'):expected={'S-01':'failed','S-02':'failed' if org=='single' else 'completed'}
                _,problems=provenance(report,ROOT/'dataset/Documents')
                checks={'outcomes':states==expected,'provenance':not problems,'automatic_cleanup':body['session_closed'] is True,
                        **{'mortgage/'+k:v for k,v in mortgage(report).items()},**({'tax/'+k:v for k,v in tax(report).items()} if 'S-02' in scenarios else {}),**({'tax_review/'+k:v for k,v in tax_review(report).items()} if 'S-02' in scenarios else {})}
                for reference in report.get('comparison_references',[]):
                    _,sha=verify_reference(reference['evidence'],reference['scenario'],profile)
                    checks[reference['scenario']+'/reference_receipt']=sha==reference['source_sha256'] and reference['gateway_receipt_verified'] is True and reference['institutional_live_retrieval'] is False
                pairs=[p for p in report['consistency']['comparisons'] if {p['left']['observation_id'],p['right']['observation_id']}=={'shared-reference-S-01','shared-reference-S-02'}]
                if profile in {'nominal','conflict_agents','conflict_document','equivalent_units','different_period','different_product'} and all(s=='completed' for s in states.values()):
                    checks['common_comparison']=len(pairs)==1 and pairs[0]['status']=={'conflict_agents':'conflict','different_period':'not_comparable','different_product':'not_comparable'}.get(profile,'consistent')
                if profile.startswith('conflict_'):checks['conflict_preserved']=report['consistency']['unresolved_conflicts']>0
                if profile=='source_timeout':checks['source_not_model_timeout']=body['activities']['S-01']['error_code']=='timeout'
                closed=(await client.delete('/sessions/'+sid)).status_code==404
                row={'utility_before_schema':utility_result,'utility_threshold_satisfied':utility_result['ratio']>=.95 if utility_result else None,'case':case,'variant':profile,'status':body['status'],'activities':{s:{'status':a['status'],'error_code':a.get('error_code'),'phases':a.get('phases',[])} for s,a in body['activities'].items()},'checks':checks,'cleanup_verified':closed,'passed':all(checks.values()) and closed,
                     'model_mode':'controlled_fixture_not_actual_ollama','human_quality':'not_automatically_assessed'}
                # Il verificatore esistente è sincrono: eseguirlo su un client separato.
                def trace():
                    with httpx.Client(base_url='http://127.0.0.1:8080',timeout=10,trust_env=False) as sync:
                        record_trace(sync,row,identifier,organization=org,minimization=policy)
                await asyncio.to_thread(trace)
                waits=[span for span in row.get('trace',{}).get('spans',[]) if span['phase']=='bridge_wait' and span['outcome']=='completed']
                row['controlled_model_execution_verified']=all(span['metrics'].get('execution_controlled_fixture')==1 and span['metrics'].get('host_http_dispatch_attempts')==0 for span in waits)
                row['passed']=row['passed'] and row['trace_verified'] and row['controlled_model_execution_verified']
                if profile.startswith('card_'):row['passed']=row['passed'] and row['trace']['summary']['a2a_message_dispatch_attempts']==(0 if org=='single' else 1)
                if profile in {'payload_identifier','payload_financial'}:row['passed']=row['passed'] and row['trace']['summary']['tool_permits_issued']==0
                rows.append(row)
                if not row['passed']:raise ValueError('Una verifica funzionale non corrisponde all’esito atteso')
                print(args.cell,profile,case,'passed: True pulizia: True',flush=True)
                boots={s:a.get('result',{}).get('measurements',{}).get('agent_boot_id') for s,a in body['activities'].items()}
                return digest(normalized(report)),boots
            finally:
                worker.cancel();await asyncio.gather(worker,return_exceptions=True)
                await asyncio.sleep(.1)
                if sid:await client.delete('/sessions/'+sid)
        try:
            await configure(initial=True)
            isolation=args.output.with_suffix('.isolation.json')
            args._procedure={'variant':'s03_preflight','output':isolation.name}
            await asyncio.to_thread(command,[sys.executable,'scripts/check_isolation.py','--output',str(isolation)])
            assert json.loads(isolation.read_text())['passed']
            rows.append({'variant':'s03_preflight','passed':True,'output':isolation.name})
            original,boots=await run_case()
            baseline_health=(await client.get('/health')).json()
            async def image_ids():
                result={}
                for role in ['gateway','markets']+(['tax'] if org=='multi' else []):
                    cid=await asyncio.to_thread(command,base+['ps','-q',role])
                    result[role]=(await asyncio.to_thread(command,[controller.docker,'inspect','--format','{{.Image}}',cid.strip()])).strip()
                return result
            original_images=await image_ids()
            assert len(set(original_images.values()))==1
            substitution_boots=[baseline_health['gateway_boot_id']]
            for case in ['C024','C006','C011','C016']:await run_case(case=case)
            # V-03: il manifest ammette esattamente i tre artefatti, poi li rifiuta il parser.
            for kind in ['scan','encrypted','corrupt']:
                raw=(ROOT/f'gateway/fixtures/verification_{kind}.pdf').read_bytes()
                reply=await client.post('/sessions/pdf',files=[('files',('negative.pdf',raw,'application/pdf'))],data={'scenarios':['S-01','S-02']})
                assert reply.status_code==400
                trace=(await client.get('/traces/'+reply.headers['x-trace-id'])).json()
                assert not trace['profile_created'] and any(s['phase']=='pdf_prevalidation' for s in trace['spans'])
                rows.append({'variant':kind,'passed':True,'parser_reached':True})
            await run_case(kinds=('mutuo',),extra=(ROOT/'gateway/fixtures/verification_corrupt.pdf').read_bytes())
            await run_case(case='C006',scenarios=('S-01',))
            for profile in PROFILES[1:]:
                await configure(profile)
                await run_case(profile)
                await configure()
                _,after=await run_case()
                assert after==boots
            for implementation in ['equivalent','standard']:
                await configure(implementation=implementation)
                result,after=await run_case();assert original==result and after==boots
                current_health=(await client.get('/health')).json()
                assert {k:v for k,v in baseline_health.items() if k not in {'gateway_boot_id','market_tool_implementation'}}=={k:v for k,v in current_health.items() if k not in {'gateway_boot_id','market_tool_implementation'}}
                assert await image_ids()==original_images
                substitution_boots.append(current_health['gateway_boot_id'])
            assert len(set(substitution_boots))==3
            rows.append({'variant':'equivalent_mcp_substitution','same_images':True,'same_other_settings':True,'same_report':True,'same_agents':True,'gateway_restarted_each_phase':True,'passed':True})
            # Driver fisici esistenti: conservare anche un controllo negativo.
            async def save_check(label,operation):
                args._procedure={'variant':label}
                checked=await operation
                rows.append({'variant':label,'passed':checked['passed'],'checks':checked['checks']})
                if not checked['passed']:raise ValueError('Controllo di finalizzazione non superato')
            await save_check('cancel',cancellation(client,identity['keys']['bridge']))
            await save_check('delivery_relay',check_delivery(ControlledDemo(client,identity['keys']['bridge'])))
            await save_check('crash',check_crash(ControlledDemo(client,identity['keys']['bridge']),controller))
        finally:
            await configure()
    if args.live_pilot:
        args._procedure={'variant':'live_five_case_pilot'}
        bridge=subprocess.Popen([sys.executable,'scripts/run_experiment_bridge.py','--organization',org,'--minimization',policy],cwd=ROOT,env=os.environ.copy(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            path=args.output.with_suffix('.live.jsonl')
            await asyncio.to_thread(command,[sys.executable,'scripts/run_baseline_pilot.py','--organization',org,'--minimization',policy,'--cases','C001','C024','C006','C011','C016','--output',str(path)],None,900)
            live=[json.loads(line) for line in path.read_text().splitlines() if line]
            assert len(live)==5 and all(r['passed'] and r['cleanup_verified'] for r in live)
            rows.append({'variant':'live_five_case_pilot','passed':True,'output':path.name})
        finally:
            bridge.terminate();await asyncio.to_thread(bridge.wait,10)
    return {'scope':'four_cell_docker_functional_pilot_not_final_campaign_or_human_quality',
            'organization':org,'minimization':policy,'rows':rows,'passed':all(r['passed'] for r in rows)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'runs/block2_manual.json')
    p.add_argument('--live-pilot',action='store_true')
    p.add_argument('--cell',choices=CELLS,help=argparse.SUPPRESS)
    args=p.parse_args();args.output=args.output.resolve()
    if args.output.exists():p.error('File già presente: scegliere un nome nuovo.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.cell:
        org,policy=args.cell.split('-');os.environ.update(TESI_EXPERIMENT=org,TESI_MINIMIZATION=policy,TESI_SHARED_REFERENCE='1',TESI_VERIFICATION_PROFILE='nominal',TESI_MARKET_SOURCE='simulated',TESI_TAX_SOURCE='simulated',TESI_MCP_PROFILE='nominal',TESI_RUNTIME='local',TESI_MARKET_TOOL_IMPLEMENTATION='standard')
        try:result=asyncio.run(cell_run(args))
        except Exception:
            result={'scope':'interrupted_pilot_not_success','cell':args.cell,'phase':getattr(args,'_phase',None),'procedure':getattr(args,'_procedure',None),'rows':getattr(args,'_rows',[]),'passed':False}
        args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        raise SystemExit(0 if result['passed'] else 1)
    import shutil
    docker=shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'
    rows=[]
    try:
        command([docker,'version'])
        command([docker,'compose','-f','compose.isolated.yaml','--profile','verification','down'])
        for cell in CELLS:
            output=args.output.with_name(args.output.stem+'_'+cell+'.json')
            if output.exists():raise ValueError('Esito di cella già presente: scegliere un nome nuovo')
            cmd=[sys.executable,str(Path(__file__).resolve()),'--cell',cell,'--output',str(output)]+(['--live-pilot'] if args.live_pilot else [])
            completed=subprocess.run(cmd,cwd=ROOT,timeout=2400)
            cell_result=json.loads(output.read_text());rows.append({'cell':cell,'passed':cell_result['passed'],'output':output.name})
            if completed.returncode or not cell_result['passed']:break
            command([docker,'compose','-f','compose.isolated.yaml','--profile','verification','down'])
        if args.live_pilot and len(rows)==4:
            from check_factorial_pilot import verify
            cells={tuple(cell.split('-')):[json.loads(line) for line in args.output.with_name(args.output.stem+'_'+cell+'.live.jsonl').read_text().splitlines() if line] for cell in CELLS}
            assert all(verify(cells).values())
    except Exception:rows.append({'phase':'procedure_interrupted','passed':False})
    finally:
        # Restituisce la demo base; nessun ponte viene lasciato in background.
        try:
            command([docker,'compose','-f','compose.isolated.yaml','--profile','verification','down'])
            command([docker,'compose','-f','compose.isolated.yaml','up','-d','--no-build'])
        except Exception:rows.append({'phase':'restore_failed','passed':False})
    result={'scope':'block2_pilot_not_final_campaign','cells':rows,'passed':len(rows)==4 and all(r['passed'] for r in rows)}
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('passed:',result['passed']);raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
