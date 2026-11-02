"""Consegna interrotta o SIGKILL del solo gateway; ponte e modello controllati."""
import argparse
import asyncio
from contextlib import asynccontextmanager
from contextlib import suppress
import json
from pathlib import Path
import shutil
import subprocess
from time import monotonic
from uuid import uuid4

import httpx

if __package__:
    from .check_cancellation import BODY, ROOT
    from .run_ollama_bridge import validate_payload, execute_live_job
else:
    from check_cancellation import BODY, ROOT
    from run_ollama_bridge import validate_payload, execute_live_job


class ControlledDemo:
    """Solo C001 e fixture locali; nessun contenuto nei risultati salvati."""
    def __init__(self, client, key):
        self.client = client
        self.headers = {'x-tesi-service-key':key}
        self.sessions = []
        self.running = []

    async def health(self):
        response = await self.client.get('/health')
        response.raise_for_status()
        body = response.json()
        if (body.get('runtime_mode'),body.get('experiment'),body.get('market_source'),body.get('tax_source')) != ('isolated','off','simulated','simulated'):
            raise ValueError('Serve la demo isolata base con fonti simulate e ponte ordinario fermo.')
        boot = body.get('gateway_boot_id')
        if not isinstance(boot,str) or len(boot)!=32 or any(c not in '0123456789abcdef' for c in boot):
            raise ValueError('Identificativo di avvio assente: ricostruire l’immagine aggiornata.')
        return boot

    async def upload(self):
        response = await self.client.post('/sessions/pdf',files=[('files',(kind+'.pdf',
            (ROOT/'dataset/Documents'/f'C001_{kind}.pdf').read_bytes(),'application/pdf')) for kind in ['mutuo','interessi']],
            data={'scenarios':['S-01','S-02']})
        response.raise_for_status()
        sid = response.json()['session_id']
        self.sessions.append(sid)
        return sid

    def start(self, sid, client=None):
        pending = asyncio.create_task((client or self.client).post(f'/sessions/{sid}/analysis'))
        self.running.append(pending)
        return pending

    async def claim(self):
        response = await self.client.get('/_bridge/poll',headers=self.headers)
        if response.status_code!=200:
            raise ValueError('Incarichi non ricevuti: controllare agenti e arresto del ponte ordinario.')
        job = response.json()
        validate_payload(job['payload'])
        return job

    async def get(self, url, **kwargs):
        # Adattatore autenticato per il controllo di validità del ponte host.
        return await self.client.get(url,headers=self.headers,**kwargs)

    async def deliver(self, job):
        return await self.client.post('/_bridge/result/'+job['job_id'],headers=self.headers,
            json={'body':BODY,'error':None,'ollama_ms':0,'source_ms':None,
                  'execution':{'kind':'controlled_fixture','dispatch_attempts':0,'responses_observed':0}})

    async def complete_two(self):
        jobs = []
        for _ in range(2):
            job = await self.claim()
            jobs.append(job)
            response = await self.deliver(job)
            response.raise_for_status()
        return jobs

    def record_result(self, result, checks, prefix):
        checks[prefix+'_completed'] = result.get('status')=='completed' and result.get('report') is not None
        ids = {s:a.get('result',{}).get('measurements',{}).get('agent_boot_id') for s,a in result.get('activities',{}).items()}
        if set(ids)!={'S-01','S-02'} or not all(ids.values()):
            raise ValueError('Avvii degli agenti assenti: prova di recupero non conclusiva.')
        return ids

    async def closed(self, sid, checks, prefix):
        checks[prefix+'_session_absent'] = (await self.client.delete('/sessions/'+sid)).status_code==404
        for scenario in ['S-01','S-02']:
            response = await self.client.post(f'/sessions/{sid}/views',json={
                'scenario':scenario,'recipient':'markets' if scenario=='S-01' else 'tax'})
            checks[prefix+'_'+scenario+'_view_absent'] = response.status_code==404

    async def stale(self, jobs, checks, prefix):
        statuses = [await self.client.get('/_bridge/status/'+job['job_id'],headers=self.headers) for job in jobs]
        results = [await self.deliver(job) for job in jobs]
        checks[prefix+'_jobs_absent'] = all(r.status_code==409 for r in statuses)
        checks[prefix+'_late_results_denied'] = all(r.status_code==409 for r in results)

    async def nominal(self, checks, prefix):
        sid = await self.upload()
        running = self.start(sid)
        await self.complete_two()
        response = await running
        response.raise_for_status()
        ids = self.record_result(response.json(),checks,prefix)
        await self.closed(sid,checks,prefix)
        return ids

    async def cleanup(self):
        for sid in self.sessions:
            try:
                await self.client.delete('/sessions/'+sid,timeout=5)
            except httpx.HTTPError:
                pass
        for pending in self.running:
            if not pending.done():
                pending.cancel()
        await asyncio.gather(*self.running,return_exceptions=True)


@asynccontextmanager
async def failing_delivery_relay(lab, sid, checks, ids):
    """Relay loopback di un solo percorso: elimina il corpo dopo il risultato completo.

    Il gateway consegna al relay; la consegna all'utente fallisce. Il test ASGI
    separato copre invece l'eccezione durante l'invio diretto dal gateway.
    """
    handlers = set()
    async def handle(reader, writer):
        current = asyncio.current_task();handlers.add(current)
        try:
            header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),5)
            if header.split(b'\r\n',1)[0]!=f'POST /sessions/{sid}/analysis HTTP/1.1'.encode():
                raise ValueError('Percorso della prova non valido')
            upstream = await lab.client.post(f'/sessions/{sid}/analysis')
            upstream.raise_for_status()
            result = upstream.json()
            ids.update(lab.record_result(result,checks,'upstream'))
            checks['report_generated_before_delivery_fault'] = result.get('report') is not None
            # Dichiara un corpo ma chiude senza consegnarne alcun byte.
            writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 1\r\nConnection: close\r\n\r\n')
            await writer.drain()
            checks['application_body_bytes_delivered_zero'] = True
            checks['relay_finished_as_configured'] = True
        except Exception:
            checks['relay_finished_as_configured'] = False
        finally:
            writer.close()
            with suppress(ConnectionError):await writer.wait_closed()
            handlers.discard(current)
    server = await asyncio.start_server(handle,'127.0.0.1',0,limit=8192)
    try:
        yield f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}'
    finally:
        server.close();await server.wait_closed()
        if handlers:
            done,pending = await asyncio.wait(handlers,timeout=5)
            for task in pending:task.cancel()
            await asyncio.gather(*done,*pending,return_exceptions=True)


async def check_delivery(lab):
    checks = {}
    boot = await lab.health()
    before = await lab.nominal(checks,'before')
    sid = await lab.upload()
    ids = {}
    try:
        async with failing_delivery_relay(lab,sid,checks,ids) as base:
            async with httpx.AsyncClient(base_url=base,timeout=35,trust_env=False,follow_redirects=False) as downstream:
                request = lab.start(sid,downstream)
                jobs = await lab.complete_two()
                try:
                    await request
                except httpx.RemoteProtocolError:
                    checks['client_delivery_failed'] = True
                else:
                    checks['client_delivery_failed'] = False
        await lab.closed(sid,checks,'failed_delivery')
        await lab.stale(jobs,checks,'failed_delivery')
        after = await lab.nominal(checks,'recovery')
        checks['same_gateway_boot'] = boot==await lab.health()
        checks['same_agent_processes'] = before==ids==after
    finally:
        await lab.cleanup()
    return result('downstream_delivery_fault_with_controlled_bridge_not_actual_ollama_or_final_campaign',checks)


class DockerGateway:
    """Comandi fissi sul solo servizio gateway del progetto corrente."""
    def __init__(self):
        executable = shutil.which('docker')
        if executable is None:
            candidate = Path('/Applications/Docker.app/Contents/Resources/bin/docker')
            executable = str(candidate) if candidate.is_file() else None
        if executable is None:
            raise ValueError('Comando Docker non disponibile.')
        self.docker = executable
        self.compose = [executable,'compose','-f','compose.isolated.yaml']
        self.cid = None
        self.marker = 'tesi-finalization-'+uuid4().hex

    async def run(self, command):
        def execute():
            response = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=45)
            if response.returncode:
                raise ValueError('Comando Docker della prova non riuscito; controllare lo stato del gateway.')
            return response.stdout.strip()
        return await asyncio.to_thread(execute)

    async def info(self):
        return json.loads(await self.run([self.docker,'inspect',self.cid]))[0]

    async def prepare(self, checks):
        self.cid = await self.run(self.compose+['ps','-q','gateway'])
        if not self.cid or '\n' in self.cid:
            raise ValueError('Serve un unico container gateway attivo.')
        data = await self.info()
        host = data['HostConfig']
        checks['gateway_storage_volatile'] = (host['ReadonlyRootfs'] and '/tmp' in (host.get('Tmpfs') or {})
            and all(m['Type']=='tmpfs' or m['Destination']=='/run/secrets/identity' and not m['RW'] for m in data['Mounts']))
        if not checks['gateway_storage_volatile']:
            raise ValueError('Configurazione di memoria e volumi diversa dal perimetro della prova.')
        code = 'from pathlib import Path;p=Path("/tmp/'+self.marker+'");p.write_text("controlled-marker");print(p.is_file())'
        checks['tmpfs_positive_marker_created'] = await self.run(self.compose+['exec','-T','gateway','python','-c',code])=='True'
        if not checks['tmpfs_positive_marker_created']:
            raise ValueError('Controllo positivo del file temporaneo non riuscito.')

    async def kill(self, checks):
        await self.run(self.compose+['kill','-s','SIGKILL','gateway'])
        state = (await self.info())['State']
        checks['forced_exit_137_observed'] = not state['Running'] and state['ExitCode']==137 and not state['OOMKilled']

    async def start(self):
        await self.run(self.compose+['start','gateway'])

    async def temporary_absent(self):
        code = 'from pathlib import Path;print(not Path("/tmp/'+self.marker+'").exists())'
        return await self.run(self.compose+['exec','-T','gateway','python','-c',code])=='True'


async def wait_ready(lab, seconds=30):
    deadline = monotonic()+seconds
    while True:
        try:
            return await lab.health()
        except httpx.HTTPError:
            if monotonic()>=deadline:
                raise ValueError('Gateway non tornato disponibile entro il limite della prova.') from None
            await asyncio.sleep(.2)


async def check_crash(lab, controller):
    checks = {}
    old_boot = await lab.health()
    before = await lab.nominal(checks,'before')
    await controller.prepare(checks)
    restarted = False
    requests = []
    try:
        sid = await lab.upload()
        pending = lab.start(sid)
        jobs = [await lab.claim(),await lab.claim()]
        checks['two_bridge_jobs_active_before_crash'] = len({j['job_id'] for j in jobs})==2
        entered = [asyncio.Event(),asyncio.Event()]
        stopped = [asyncio.Event(),asyncio.Event()]
        async def model_request(request):
            index = next(i for i,event in enumerate(entered) if not event.is_set())
            entered[index].set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped[index].set()
        async with httpx.AsyncClient(transport=httpx.MockTransport(model_request)) as model:
            for job in jobs:
                requests.append(asyncio.create_task(execute_live_job(job,lab,model)))
            await asyncio.wait_for(asyncio.gather(*(event.wait() for event in entered)),5)
            await controller.kill(checks)
            try:
                await asyncio.wait_for(pending,10)
            except httpx.TransportError:
                checks['inflight_http_interrupted'] = True
            else:
                checks['inflight_http_interrupted'] = False
            replies = await asyncio.wait_for(asyncio.gather(*requests),10)
            checks['host_bridge_requests_cancelled_on_gateway_loss'] = all(event.is_set() for event in stopped) and replies==[None,None]
        await controller.start()
        new_boot = await wait_ready(lab)
        restarted = True
        checks['new_gateway_boot_observed'] = old_boot!=new_boot
        checks['temporary_artifact_absent_after_restart'] = await controller.temporary_absent()
        await lab.closed(sid,checks,'old')
        await lab.stale(jobs,checks,'old')
        after = await lab.nominal(checks,'recovery')
        checks['same_agent_processes'] = before==after
    finally:
        for request in requests:
            if not request.done():request.cancel()
        await asyncio.gather(*requests,return_exceptions=True)
        if not restarted:
            await controller.start()
        await lab.cleanup()
    return result('isolated_gateway_sigkill_with_controlled_model_not_power_loss_or_final_campaign',checks)


def result(scope, checks):
    return {'scope':scope,'case':'C001','checks':checks,'passed':bool(checks) and all(value is True for value in checks.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['delivery','crash'],required=True,
        help='delivery: interrompe la consegna al client; crash: SIGKILL e riavvio del solo gateway Docker.')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():parser.error('File già presente: usare un nome nuovo.')
    identity = json.loads((ROOT/'.local/s03/bridge.json').read_text())
    if identity.get('role')!='bridge':parser.error('Identità del ponte non valida.')
    async def run():
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8080',timeout=35,trust_env=False,follow_redirects=False) as client:
            lab = ControlledDemo(client,identity['keys']['bridge'])
            return await (check_delivery(lab) if args.mode=='delivery' else check_crash(lab,DockerGateway()))
    try:
        data = asyncio.run(asyncio.wait_for(run(),150))
    except (ValueError,TimeoutError,httpx.HTTPError) as error:
        if type(error) is ValueError:parser.error(str(error))
        parser.error('Prova non completata: controllare servizi e ponte ordinario fermo. Nessun successo registrato.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')
    for name,value in data['checks'].items():print(name+':',value)
    print('passed:',data['passed'])
    raise SystemExit(0 if data['passed'] else 1)


if __name__=='__main__':main()
