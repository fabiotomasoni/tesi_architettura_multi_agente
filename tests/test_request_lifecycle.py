"""Il producer appartiene alla richiesta fino alla fine della coda SDK."""
import asyncio
from contextlib import suppress
from types import SimpleNamespace
from uuid import uuid4

from a2a.server.events import EventQueue
from a2a.types import Message, Role, Part, TextPart
from services.request_lifecycle import A2aAgentExecutor, RequestExecutor, SingleRequestApp


def test_disconnect_cancels_producer_after_execute_while_sdk_queue_is_closing(monkeypatch):
    async def exercise():
        emitted=asyncio.Event()
        finished=asyncio.Event()
        producers=[]
        queues=[]
        async def execute(self,context,event_queue):
            await event_queue.enqueue_event(Message(message_id=uuid4().hex,role=Role.agent,
                parts=[Part(root=TextPart(text='Evento controllato della fixture.'))]))
            emitted.set()
        monkeypatch.setattr(A2aAgentExecutor,'execute',execute)
        # Nessun runner viene invocato dalla fixture del producer.
        executor=object.__new__(RequestExecutor)
        class Sessions:
            async def list_sessions(self,**kwargs):return SimpleNamespace(sessions=[])
        store=SimpleNamespace(lock=asyncio.Lock(),tasks={})
        calls=[]
        async def inner(scope,receive,send):
            calls.append(True)
            if len(calls)==1:
                queue=EventQueue();queues.append(queue)
                async def producer():
                    try:
                        await executor.execute(None,queue)
                        # Il consumer è già uscito: la chiusura graceful SDK
                        # attende l'evento ancora da consumare.
                        await queue.close()
                    finally:finished.set()
                task=asyncio.create_task(producer());producers.append(task)
                try:await asyncio.shield(task)
                finally:
                    # Come il cleanup SDK: attende il producer anche dopo
                    # la cancellazione della richiesta che lo possiede.
                    with suppress(asyncio.CancelledError):await task
            else:
                await send({'type':'http.response.start','status':200,'headers':[]})
                await send({'type':'http.response.body','body':b''})
        app=SingleRequestApp(inner,Sessions(),store,'controlled')
        incoming=asyncio.Queue()
        scope={'type':'http','method':'POST'}
        sent=[]
        async def send(message):sent.append(message)
        running=asyncio.create_task(app(scope,incoming.get,send))
        try:
            await asyncio.wait_for(emitted.wait(),1)
            # execute è tornato, ma il task producer è ancora in queue.close.
            await asyncio.sleep(0)
            assert not producers[0].done() and queues[0].is_closed()
            incoming.put_nowait({'type':'http.disconnect'})
            done,_=await asyncio.wait({running},timeout=1)
            assert running in done,'La coda SDK non deve trattenere il lock della richiesta annullata'
            await running
            assert finished.is_set() and producers[0].done() and not app.lock.locked()
            assert not store.tasks
            # Il medesimo oggetto/processo deve accettare una nuova richiesta.
            await asyncio.wait_for(app(scope,asyncio.Queue().get,send),1)
            assert sent[0]['status']==200 and len(calls)==2 and not app.lock.locked()
        finally:
            for task in producers:
                if not task.done():task.cancel()
            if not running.done():running.cancel()
            await asyncio.gather(running,*producers,return_exceptions=True)
    asyncio.run(exercise())
