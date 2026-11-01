"""SIGKILL reale di un gateway temporaneo; deleghe controllate, nessun Docker o LLM."""
import asyncio
from contextlib import suppress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import httpx
import pytest

from scripts.check_finalization import ControlledDemo, DockerGateway, check_crash, wait_ready

ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import asyncio, importlib, json, os, tempfile
import uvicorn
from gateway.inference import InferenceBroker, InferenceRequest, MODELS
from gateway.agent_contracts import MarketResult, TaxResult
from gateway.market_evidence import expected_evidence as markets
from gateway.tax_evidence import expected_evidence as taxes
module=importlib.import_module('gateway.app')
broker=InferenceBroker()
module.InferenceBroker=lambda:broker
async def remote(task):
    evidence=(markets if task.scenario=='S-01' else taxes)(task.view)
    reply=await broker.infer(InferenceRequest(correlation_id=task.correlation_id,scenario=task.scenario,evidence=evidence.model_dump(mode='json')),'Bearer '+task.inference_token)
    return (MarketResult if task.scenario=='S-01' else TaxResult)(correlation_id=task.correlation_id,status='completed',evidence=evidence,summary=reply.summary,limits=[],model=MODELS[task.scenario],measurements={'agent_boot_id':'controlled-delegate-'+task.scenario})
import gateway.market_client, gateway.tax_client
gateway.market_client.delegate=remote
gateway.tax_client.delegate=remote
# Segnale positivo del rollover reale multipart: nessun nome/contenuto/token.
original=tempfile.TemporaryFile
def tracked(*args,**kwargs):
    stream=original(*args,**kwargs)
    print('SPOOL_UNLINKED' if os.fstat(stream.fileno()).st_nlink==0 else 'SPOOL_NAMED',flush=True)
    return stream
tempfile.TemporaryFile=tracked
uvicorn.run(module.create_app(),fd=int(os.environ['TESI_TEST_FD']),log_level='critical',access_log=False,proxy_headers=False)
'''


class ProcessGateway:
    def __init__(self, directory):
        self.directory = directory
        self.spool = directory/'spool';self.spool.mkdir()
        self.socket = socket.socket();self.socket.bind(('127.0.0.1',0));self.socket.listen(128)
        self.base = 'http://127.0.0.1:'+str(self.socket.getsockname()[1])
        self.key = '5'.zfill(64)
        keys={name:format(i,'064x') for i,name in enumerate(
            ['gateway_to_markets','gateway_to_tax','markets_to_gateway','tax_to_gateway','bridge'],1)}
        identity = directory/'identity.json';identity.write_text(json.dumps({'role':'gateway','keys':keys}))
        self.env={**os.environ,'TESI_RUNTIME':'isolated','TESI_EXPERIMENT':'off','TESI_MINIMIZATION':'active',
            'TESI_MARKET_SOURCE':'simulated','TESI_TAX_SOURCE':'simulated','TESI_MCP_PROFILE':'nominal',
            'TESI_IDENTITY_FILE':str(identity),'LANGSMITH_TRACING':'false','PYTHONDONTWRITEBYTECODE':'1',
            'TMPDIR':str(self.spool),'TESI_TEST_FD':str(self.socket.fileno())}
        self.process = None
        self.writer = None

    async def start(self):
        if self.process is not None:
            assert self.process.poll() is not None, 'Non avviare due gateway sullo stesso socket'
            self.process.stdout.close()
        self.process=subprocess.Popen([sys.executable,'-c',CHILD],cwd=ROOT,env=self.env,
            pass_fds=(self.socket.fileno(),),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)

    async def prepare(self, checks):
        # Il parser riceve >1 MiB del file, poi resta in attesa del resto.
        # Si interrompe il processo mentre il file di spool è realmente aperto.
        _,self.writer=await asyncio.open_connection('127.0.0.1',self.socket.getsockname()[1])
        prefix=b'--fixture\r\nContent-Disposition: form-data; name="files"; filename="fixture.pdf"\r\nContent-Type: application/pdf\r\n\r\n'
        content=(ROOT/'dataset/Documents/C001_mutuo.pdf').read_bytes()+b' '*(1024*1024+1000)
        headers=(f'POST /sessions/pdf HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: multipart/form-data; boundary=fixture\r\nContent-Length: {len(prefix)+len(content)+100000}\r\n\r\n').encode()
        self.writer.write(headers+prefix+content);await self.writer.drain()
        signal=await asyncio.wait_for(asyncio.to_thread(self.process.stdout.readline),5)
        checks['actual_partial_upload_spool_unlinked_while_open'] = signal==b'SPOOL_UNLINKED\n'
        assert checks['actual_partial_upload_spool_unlinked_while_open']

    async def kill(self, checks):
        self.process.kill()
        await asyncio.to_thread(self.process.wait,5)
        checks['actual_native_sigkill_observed'] = self.process.returncode==-9
        self.writer.close()
        with suppress(ConnectionError):await self.writer.wait_closed()

    async def temporary_absent(self):
        return not list(self.spool.iterdir())

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill();self.process.wait(5)
            self.process.stdout.close()
        self.socket.close()


@pytest.mark.skipif(os.name=='nt',reason='Prova nativa POSIX di SIGKILL/fd; Docker Linux verificato separatamente')
def test_actual_sigkill_discards_sessions_jobs_and_open_upload_spool_then_recovers(tmp_path,monkeypatch):
    controller=ProcessGateway(tmp_path)
    # Il ponte resta vincolato al solo gateway loopback temporaneo del test.
    monkeypatch.setattr('scripts.run_ollama_bridge.BASE',controller.base)
    async def exercise():
        await controller.start()
        async with httpx.AsyncClient(base_url=controller.base,timeout=15,trust_env=False,follow_redirects=False) as client:
            lab=ControlledDemo(client,controller.key)
            await wait_ready(lab,10)
            result=await check_crash(lab,controller)
            assert result['passed'],result
            assert result['checks']['actual_native_sigkill_observed']
            assert result['checks']['new_gateway_boot_observed']
            assert result['checks']['host_bridge_requests_cancelled_on_gateway_loss']
            assert result['checks']['actual_partial_upload_spool_unlinked_while_open']
            assert result['checks']['temporary_artifact_absent_after_restart']
    try:asyncio.run(exercise())
    finally:controller.close()


@pytest.mark.parametrize('fault',['writable_root','persistent_data_mount','no_tmpfs'])
def test_docker_crash_preflight_refuses_unexpected_storage_without_killing(fault):
    controller=object.__new__(DockerGateway)
    controller.compose=['docker','compose','-f','compose.isolated.yaml']
    controller.docker='docker';controller.marker='controlled';controller.cid=None
    config={'HostConfig':{'ReadonlyRootfs':True,'Tmpfs':{'/tmp':'rw'}},
            'Mounts':[{'Type':'bind','Destination':'/run/secrets/identity','RW':False}]}
    if fault=='writable_root':config['HostConfig']['ReadonlyRootfs']=False
    if fault=='persistent_data_mount':config['Mounts'].append({'Type':'volume','Destination':'/data','RW':True})
    if fault=='no_tmpfs':config['HostConfig']['Tmpfs']=None
    commands=[]
    async def run(command):
        commands.append(command)
        if command[-3:]==['ps','-q','gateway']:return 'controlled-container'
        if 'inspect' in command:return json.dumps([config])
        pytest.fail('Mutazione prima del completamento del controllo preventivo')
    controller.run=run
    with pytest.raises(ValueError,match='memoria e volumi'):
        asyncio.run(controller.prepare({}))
    assert not any('kill' in command or 'start' in command for command in commands)
