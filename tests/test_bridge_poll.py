"""Un poll HTTP disconnesso non deve ritirare il job della richiesta successiva."""
import asyncio
import httpx
from gateway.inference import InferenceBroker
from gateway.ollama_bridge import OllamaBridge

def test_disconnected_long_poll_does_not_steal_next_job(monkeypatch,local_gateway):
    import gateway.app as module
    broker=InferenceBroker();broker.bridge=OllamaBridge()
    monkeypatch.setattr(module,'InferenceBroker',lambda:broker)
    app=module.create_app();tasks=[];finished=[]
    original_poll=broker.bridge.poll
    async def observed_poll():
        try:return await original_poll()
        finally:finished.append(True)
    broker.bridge.poll=observed_poll
    @app.post('/test/enqueue')
    async def enqueue():
        tasks.append(asyncio.create_task(broker.bridge.infer({'model':'controlled'},3,owner='test')))
        return {}
    @app.post('/test/end')
    async def end():
        broker.bridge.revoke('test');await asyncio.gather(*tasks,return_exceptions=True)
        return {}
    async def exercise(base):
        async with httpx.AsyncClient(base_url=base,trust_env=False,timeout=2) as client:
            polling=asyncio.create_task(client.get('/_bridge/poll'))
            for _ in range(100):
                if broker.bridge.queue._getters:break
                await asyncio.sleep(.01)
            assert broker.bridge.queue._getters
            polling.cancel();await asyncio.gather(polling,return_exceptions=True)
            for _ in range(100):
                if not broker.bridge.queue._getters and finished:break
                await asyncio.sleep(.01)
            assert not broker.bridge.queue._getters and finished
            enqueued=await client.post('/test/enqueue');assert enqueued.status_code==200
            for _ in range(100):
                if broker.bridge.pending:break
                await asyncio.sleep(.01)
            assert len(broker.bridge.pending)==1 and broker.bridge.queue.qsize()==1,(len(broker.bridge.pending),broker.bridge.queue.qsize(),len(broker.bridge.queue._getters),len(finished))
            reply=await client.get('/_bridge/poll')
            assert reply.status_code==200 and reply.json()['payload']=={'model':'controlled'}
            await client.post('/test/end')
            assert not broker.bridge.pending
    with local_gateway(app) as base:asyncio.run(exercise(base))
