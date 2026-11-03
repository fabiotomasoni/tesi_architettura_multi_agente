"""Runner locale: pilota distinto dalla campagna congelata, senza retry impliciti."""
import argparse,asyncio,json,os,shutil,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scripts.campaign_support import ROOT,Collector,read,write_new,digest,verify_bundle,check_approval,reference_checks,result_hashes,require_cold_models,actual_model_receipts
from scripts.prepare_campaign import environment


def commands(org,policy):
    docker=shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'
    cmd=[docker,'compose','-f','compose.isolated.yaml','-f','compose.experiment-'+org+'.yaml']
    if policy=='disabled':cmd+=['-f','compose.experiment-unminimized.yaml']
    return cmd+['-f','compose.verification.yaml','--profile','verification']


def call(args, *, timeout=180):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise ValueError('Procedura non completata; evidenze conservate, nessun retry automatico.')
    return result.stdout


def settings():
    return {k:v for k,v in os.environ.items() if not k.startswith('TESI_')}


async def base_cases(folder,block):
    import httpx
    from scripts.trace_export import record_trace
    from scripts.evaluation_support import utility
    from scripts.check_block1 import verify_report
    collector=Collector(folder,block,'base');org,policy=block['cell'].split('-')
    factory=collector.async_factory(lambda:collector.context)
    async with factory(base_url='http://127.0.0.1:8080',timeout=150,trust_env=False) as client:
        h=(await client.get('/health')).json()
        if (h.get('experiment'),h.get('minimization'),h.get('market_source'),h.get('tax_source'),h.get('shared_reference'))!=(org,policy,'simulated','simulated',True):raise ValueError('Cella nominale non conforme: nessun PDF inviato.')
        finished=False
        try:
            for case in block['cases']:
                collector.context={'case':case,'variant':'nominal'};sid=None;row=None
                try:
                    files=[('files',(kind+'.pdf',(ROOT/f'dataset/Documents/{case}_{kind}.pdf').read_bytes(),'application/pdf')) for kind in ('mutuo','interessi')]
                    r=await client.post('/sessions/pdf',files=files,data={'scenarios':['S-01','S-02']});r.raise_for_status();sid=r.json()['session_id'];row=collector.sessions[sid]
                    for scenario,recipient in [('S-01','markets'),('S-02','tax')]:
                        view=await client.post('/sessions/'+sid+'/views',json={'scenario':scenario,'recipient':recipient})
                        required=collector.annotations[case]['agent_utility_facts'][scenario]
                        row.setdefault('utility',{})[scenario]=utility(view.json().get('data',{}),required)
                    response=await client.post('/sessions/'+sid+'/analysis');response.raise_for_status();body=response.json()
                    expected=collector.annotations[case]['expected_activities']
                    report=body['report']
                    checks=verify_report(report,expected,real_sources=False,minimization=policy)
                    checks.update(reference_checks(report,collector.annotations[case]))
                    row['deterministic_financial_sha256']=digest({k:report.get(k) for k in ('status','mortgage_comparison','mortgage_contract_analysis','tax_application')})
                    checks['outcomes']={s:a['status'] for s,a in body['activities'].items()}==expected
                    checks['same_model']=all(a.get('result',{}).get('model')=='llama3.2:3b' for a in body['activities'].values() if a['status']=='completed')
                    checks['reference_receipts']=all(a.get('result',{}).get('measurements',{}).get('gateway_reference_receipt_verified')==1 for a in body['activities'].values() if a['status']=='completed')
                    row['checks']=checks;row['passed']=all(checks.values())
                    def trace():
                        with httpx.Client(base_url='http://127.0.0.1:8080',trust_env=False,timeout=10) as c:record_trace(c,row,row['trace_id'],organization=org,minimization=policy)
                    await asyncio.to_thread(trace)
                    checks['actual_ollama_execution']=actual_model_receipts(row.get('trace',{}),sum(v=='completed' for v in expected.values()))
                    row['passed']=all(checks.values()) and row['trace_verified']
                except (httpx.HTTPError,ValueError,KeyError,TypeError):
                    if row is None:row=collector.rows[-1] if collector.rows else None
                    if row is not None:row.update(passed=False,error_category='request_or_validation_failed')
                finally:
                    if sid:
                        try:await client.delete('/sessions/'+sid)
                        except httpx.HTTPError:pass
                if row is None or row.get('profile_created') is not False and not row['cleanup_verified']:raise ValueError('Pulizia non confermata: campagna arrestata senza eliminare l’esito.')
                print(block['id'],case,row['status'],'passed:',row.get('passed',False),'pulizia:',row['cleanup_verified'],flush=True)
            finished=True
        finally:
            rows=collector.finish(procedure_passed=finished)
            write_new(Path(folder)/'private/base'/(block['id']+'.json'),{'rows':rows,'passed':all(r.get('passed') for r in rows)})
    return rows


async def controlled(folder,block):
    from scripts.check_block2 import cell_run
    collector=Collector(folder,block,'controlled')
    args=SimpleNamespace(cell=block['cell'],output=Path(folder)/'private/controlled'/(block['id']+'.json'),live_pilot=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.client_factory=collector.async_factory(lambda:getattr(args,'_procedure',{'case':'C001','variant':'nominal'}))
    passed=False
    try:
        result=await cell_run(args);passed=result['passed']
        known=[r for r in result['rows'] if 'activities' in r]
        used=set()
        for row in collector.rows:
            for i,checked in enumerate(known):
                if i not in used and checked.get('case')==row['case'] and checked.get('variant')==row['variant']:
                    row['passed']=checked['passed'];row['checks']=checked['checks'];used.add(i);break
        write_new(args.output,result)
    finally:
        rows=collector.finish(procedure_passed=passed)
        write_new(Path(folder)/'private/observations'/(block['id']+'.json'),{'passed':passed,'rows':rows})
    return rows


def execute_block(bundle,folder,block):
    org,policy=block['cell'].split('-')
    os.environ.update(settings())
    for key in list(os.environ):
        if key.startswith('TESI_'):del os.environ[key]
    os.environ.update(TESI_RUNTIME='local',TESI_EXPERIMENT=org,TESI_MINIMIZATION=policy,TESI_SHARED_REFERENCE='1',TESI_VERIFICATION_PROFILE='nominal',TESI_MARKET_SOURCE='simulated',TESI_TAX_SOURCE='simulated',TESI_MCP_PROFILE='nominal',TESI_MARKET_TOOL_IMPLEMENTATION='standard')
    compose=commands(org,policy);call(compose+['up','-d','--no-build'])
    # Anche il preflight deve raggiungere servizi pronti. La suite controllata
    # possiede il proprio controllo d'avvio; qui aspettiamo il nominale reale.
    import httpx,time
    for _ in range(120):
        try:
            h=httpx.get('http://127.0.0.1:8080/health',trust_env=False,timeout=2).json()
            if (h.get('experiment'),h.get('minimization'),h.get('verification_profile'))==(org,policy,'nominal'):
                ready=True
                for service,port in [('markets',8001)]+([('tax',8002)] if org=='multi' else []):
                    call(compose+['exec','-T',service,'python','-c',f'import socket;s=socket.create_connection(("127.0.0.1",{port}),timeout=2);s.close()'])
                break
        except (httpx.HTTPError,ValueError):pass
        time.sleep(.25)
    else:raise ValueError('Servizi della cella non pronti.')
    require_cold_models(httpx.get('http://127.0.0.1:11434/api/ps',trust_env=False,timeout=5).json())
    preflight=Path(folder)/'private/isolation'/(block['id']+'.json');preflight.parent.mkdir(parents=True,exist_ok=True)
    call([sys.executable,'scripts/check_isolation.py','--output',str(preflight)])
    if not read(preflight)['passed']:raise ValueError('Isolamento non confermato.')
    bridge=subprocess.Popen([sys.executable,'scripts/run_experiment_bridge.py','--organization',org,'--minimization',policy],cwd=ROOT,env=os.environ.copy(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:base=asyncio.run(base_cases(folder,block))
    finally:
        bridge.terminate()
        try:bridge.wait(10)
        except subprocess.TimeoutExpired:bridge.kill();bridge.wait(10)
    controlled_rows=asyncio.run(controlled(folder,block))
    call([sys.executable,'-m','tests.campaign_finalization_worker','--directory',str(folder),'--block',block['id']],timeout=240)
    native=read(Path(folder)/'private/native'/(block['id']+'.json'))
    rows=base+controlled_rows+native['rows']
    observed={'created':sum(r['profile_created'] for r in rows),'rejected':sum(not r['profile_created'] for r in rows),'delivered':sum(r['report_delivered'] for r in rows)}
    expected={'created':len(block['cases'])+60,'rejected':3,'delivered':len(block['cases'])+55}
    count_ok=(len(rows)==len(block['cases'])+63 and sum(r['profile_created'] for r in controlled_rows+native['rows'])==60 and sum(r['report_delivered'] for r in controlled_rows+native['rows'])==55)
    write_new(Path(folder)/'private/blocks'/(block['id']+'.json'),{'block':block,'rows':rows,'observed_counts':observed,'expected_counts':expected,'counts_match':count_ok,
        'passed':count_ok and native['passed'] and all(r.get('procedure_passed') and (r.get('passed',True)) for r in rows)})
    print(block['id'],'conteggi osservati:',observed,'conteggi coerenti:',count_ok,flush=True)
    if not count_ok:raise ValueError('Conteggio fisico diverso dal piano: nessun congelamento o esito positivo implicito.')


def run(bundle, *, pilot=False, only_block=None):
    bundle=Path(bundle).resolve();errors=verify_bundle(bundle,environment=environment())
    if errors:raise ValueError('Manifest non conforme: '+', '.join(errors))
    if not pilot:check_approval(bundle)
    folder=bundle/('pilot' if pilot else 'final');schedule=read(bundle/('pilot_plan.json' if pilot else 'plan.json'))
    if only_block:
        if only_block not in {b['id'] for b in schedule['blocks']}:raise ValueError('Blocco sconosciuto.')
        blocks=[b for b in schedule['blocks'] if b['id']==only_block]
    else:blocks=schedule['blocks']
    # Nessun overwrite, nessun retry nascosto. È possibile proseguire soltanto
    # con blocchi ancora mai avviati; un blocco interrotto richiede revisione.
    folder.mkdir(parents=True,exist_ok=True)
    docker=shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'
    for block in blocks:
        if (folder/'private/started'/(block['id']+'.json')).exists():raise ValueError('Blocco già avviato: scegliere esplicitamente un blocco mai eseguito, senza sovrascrivere.')
    completed=[];active_block=None
    try:
        call([docker,'compose','-f','compose.isolated.yaml','--profile','verification','down'])
        for block in blocks:
            active_block=block['id']
            # Ogni blocco in un processo nuovo: moduli di ruolo/policy immutabili.
            if environment()!=read(bundle/'manifest.json')['environment'] or verify_bundle(bundle):raise ValueError('Ambiente o sorgenti modificati durante la procedura.')
            print('Avvio blocco',len(completed)+1,'di',len(blocks),block['id'],'casi Ollama:',len(block['cases']),flush=True)
            write_new(folder/'private/started'/(block['id']+'.json'),{'block':block['id'],'manifest_sha256':digest(read(bundle/'manifest.json'))})
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--directory',str(bundle),'--worker',block['id']]+(['--pilot'] if pilot else []),cwd=ROOT,timeout=3600)
            if result.returncode:raise ValueError('Blocco interrotto: dati conservati; nessuna ripetizione automatica.')
            if environment()!=read(bundle/'manifest.json')['environment']:raise ValueError('Ambiente o pesi cambiati durante il blocco; evidenze da rivedere.')
            completed.append(block['id'])
            call([docker,'compose','-f','compose.isolated.yaml','--profile','verification','down'])
    except BaseException as error:
        write_new(folder/'private/interruptions'/((active_block or 'preflight')+'.json'),{'category':type(error).__name__,'counted_as_success':False})
        raise
    finally:
        call([docker,'compose','-f','compose.isolated.yaml','--profile','verification','down'])
        call([docker,'compose','-f','compose.isolated.yaml','up','-d','--no-build'])
    all_blocks=[folder/'private/blocks'/(b['id']+'.json') for b in schedule['blocks']]
    if all(p.exists() for p in all_blocks):
        passed=all(read(p)['passed'] for p in all_blocks)
        write_new(folder/'completion.json',{'manifest_sha256':digest(read(bundle/'manifest.json')),'scope':schedule['scope'],'blocks':len(all_blocks),'passed':passed,'private_sha256':result_hashes(folder)})
        print('Pilota completo:' if pilot else 'Raccolta finale completa:',passed)
        if not passed:raise ValueError('Raccolta completa con verifiche negative: nessun successo complessivo attribuito.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--pilot',action='store_true');p.add_argument('--block');p.add_argument('--worker',help=argparse.SUPPRESS);a=p.parse_args()
    try:
        if a.worker:
            errors=verify_bundle(a.directory)
            if errors:raise ValueError('Manifest modificato.')
            if not a.pilot:check_approval(a.directory)
            schedule=read(a.directory/('pilot_plan.json' if a.pilot else 'plan.json'))
            block=next(b for b in schedule['blocks'] if b['id']==a.worker)
            execute_block(a.directory,a.directory/('pilot' if a.pilot else 'final'),block)
        else:run(a.directory,pilot=a.pilot,only_block=a.block)
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as e:p.error(str(e))
if __name__=='__main__':main()
