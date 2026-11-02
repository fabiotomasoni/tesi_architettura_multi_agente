"""Prova HTTP della demo isolata: ponte controllato, nessuna vera inferenza Ollama."""
import argparse
import asyncio
import json
from pathlib import Path

import httpx

if __package__:
    from .run_ollama_bridge import validate_payload
else:
    from run_ollama_bridge import validate_payload

ROOT = Path(__file__).resolve().parents[1]
BODY = {'message':{'content':'Risposta della fixture di verifica annullamento; non generata da Ollama.'},
        'prompt_eval_count':1, 'eval_count':1, 'load_duration':0}


async def check(client, key):
    health = await client.get('/health')
    health.raise_for_status()
    config = health.json()
    if (config.get('runtime_mode'),config.get('experiment'),config.get('market_source'),config.get('tax_source')) != ('isolated','off','simulated','simulated'):
        raise ValueError('Usare la demo isolata base con fonti simulate, senza profili sperimentali o fonti reali.')
    headers = {'x-tesi-service-key':key}
    sessions = []
    checks = {}

    async def upload():
        response = await client.post('/sessions/pdf',files=[('files',(kind+'.pdf',
            (ROOT/'dataset/Documents'/('C001_'+kind+'.pdf')).read_bytes(),'application/pdf')) for kind in ['mutuo','interessi']],
            data={'scenarios':['S-01','S-02']})
        response.raise_for_status()
        sid = response.json()['session_id'];sessions.append(sid)
        return sid

    async def claim():
        response = await client.get('/_bridge/poll',headers=headers)
        if response.status_code!=200:
            raise ValueError('Nessun incarico ricevuto: fermare il ponte ordinario e controllare gli agenti.')
        job = response.json()
        validate_payload(job['payload'])
        return job

    async def deliver(job):
        return await client.post('/_bridge/result/'+job['job_id'],headers=headers,
            json={'body':BODY,'error':None,'ollama_ms':0,'source_ms':None,
                  'execution':{'kind':'controlled_fixture','dispatch_attempts':0,'responses_observed':0}})

    async def nominal(label):
        sid = await upload()
        running = asyncio.create_task(client.post(f'/sessions/{sid}/analysis'))
        try:
            for _ in range(2):
                response = await deliver(await claim())
                response.raise_for_status()
            response = await running
            response.raise_for_status();result=response.json()
            checks[label+'_completed'] = result.get('status')=='completed' and result.get('report') is not None
            checks[label+'_cleanup'] = (await client.delete('/sessions/'+sid)).status_code==404
            ids = {s:a.get('result',{}).get('measurements',{}).get('agent_boot_id') for s,a in result.get('activities',{}).items()}
            if set(ids)!={'S-01','S-02'} or not all(ids.values()):
                raise ValueError('Identificativi di avvio degli agenti assenti: recupero non dimostrabile.')
            return ids
        finally:
            if not running.done():
                await client.delete('/sessions/'+sid)
                running.cancel()
            await asyncio.gather(running,return_exceptions=True)

    try:
        before = await nominal('before')
        sid = await upload()
        running = asyncio.create_task(client.post(f'/sessions/{sid}/analysis'))
        try:
            jobs = [await claim(),await claim()]
            checks['both_agents_waiting_on_bridge'] = len({job['job_id'] for job in jobs})==2
            duplicate = await client.post(f'/sessions/{sid}/analysis')
            checks['duplicate_analysis_denied'] = duplicate.status_code==409 and duplicate.json().get('detail',{}).get('error_code')=='analysis_already_running'
            deleted = await client.delete('/sessions/'+sid)
            checks['cancellation_acknowledged'] = deleted.status_code==204
            response = await asyncio.wait_for(running,10)
            result = response.json()
            checks['analysis_cancelled_without_report'] = (response.status_code==409 and result.get('status')=='cancelled'
                and result.get('error_code')=='analysis_cancelled' and result.get('session_closed') is True and 'report' not in result)
            statuses = [await client.get('/_bridge/status/'+job['job_id'],headers=headers) for job in jobs]
            checks['bridge_jobs_revoked'] = all(response.status_code==409 for response in statuses)
            late = [await deliver(job) for job in jobs]
            checks['late_results_denied'] = all(response.status_code==409 for response in late)
            checks['cancelled_session_absent'] = (await client.delete('/sessions/'+sid)).status_code==404
            for scenario in ['S-01','S-02']:
                r=await client.post(f'/sessions/{sid}/views',json={'scenario':scenario,'recipient':'markets' if scenario=='S-01' else 'tax'})
                checks[scenario+'_closed_profile_unavailable'] = r.status_code==404
        finally:
            if not running.done():
                await client.delete('/sessions/'+sid)
                running.cancel()
            await asyncio.gather(running,return_exceptions=True)
        after = await nominal('recovery')
        checks['same_agent_processes'] = before==after
    finally:
        for sid in sessions:
            await client.delete('/sessions/'+sid)
    return {'scope':'isolated_http_a2a_mcp_cancellation_with_controlled_bridge_not_actual_ollama_or_final_campaign',
            'case':'C001','checks':checks,'passed':bool(checks) and all(checks.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/cancellation_manual.json')
    args=parser.parse_args()
    if args.output.exists():
        parser.error('File già presente: usare un nome nuovo per questa prova.')
    identity=json.loads((ROOT/'.local/s03/bridge.json').read_text())
    if identity.get('role')!='bridge':
        parser.error('Identità del ponte non valida.')
    async def run():
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8080',timeout=35,trust_env=False,follow_redirects=False) as client:
            return await asyncio.wait_for(check(client,identity['keys']['bridge']),120)
    try:
        result=asyncio.run(run())
    except (ValueError,TimeoutError,httpx.HTTPError) as error:
        # Nessun corpo, chiave o dettaglio di trasporto nei log.
        if type(error) is ValueError:parser.error(str(error))
        parser.error('Prova non completata: controllare demo isolata e arresto del ponte ordinario. Nessun risultato positivo registrato.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    for name,value in result['checks'].items():
        print(name+':',value)
    print('passed:',result['passed'])
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':
    main()
