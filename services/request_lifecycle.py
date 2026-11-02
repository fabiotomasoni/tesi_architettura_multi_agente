"""La richiesta A2A singola possiede esecuzioni ADK/MCP e risorse temporanee."""
import asyncio
from contextvars import ContextVar
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

_executions = ContextVar('a2a_request_executions', default=None)


class RequestExecutor(A2aAgentExecutor):
    async def execute(self, context, event_queue):
        owned = _executions.get()
        task = asyncio.current_task()
        if owned is not None:
            owned.add(task)
            # Il task SDK continua dopo execute, anche nella chiusura della
            # coda. Rimuoverlo qui in finally lasciava producer non più
            # cancellabili dalla richiesta e poteva bloccare queue.join().
            task.add_done_callback(owned.discard)
        await super().execute(context, event_queue)


class SingleRequestApp:
    def __init__(self, inner, session_service, task_store, app_name):
        self.inner = inner
        self.session_service = session_service
        self.task_store = task_store
        self.app_name = app_name
        self.lock = asyncio.Lock()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.inner(scope, receive, send)
        incoming = asyncio.Queue(maxsize=2)
        owned = set()

        async def listen():
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                await incoming.put(message)

        async def handle():
            async with self.lock:
                token = _executions.set(owned)
                try:
                    await self.inner(scope, incoming.get, send)
                finally:
                    _executions.reset(token)
                    sessions = await self.session_service.list_sessions(app_name=self.app_name)
                    for session in sessions.sessions:
                        await self.session_service.delete_session(app_name=self.app_name, user_id=session.user_id, session_id=session.id)
                    async with self.task_store.lock:
                        self.task_store.tasks.clear()

        listener = asyncio.create_task(listen())
        running = asyncio.create_task(handle())
        try:
            done, _ = await asyncio.wait({running, listener}, return_when=asyncio.FIRST_COMPLETED)
            if running in done:
                await running
            else:
                # L'SDK crea un producer separato: annullare il solo HTTP non basta.
                for task in list(owned):
                    task.cancel()
                running.cancel()
                await asyncio.gather(running, *owned, return_exceptions=True)
        finally:
            listener.cancel()
            for task in list(owned):
                task.cancel()
            if not running.done():
                running.cancel()
            await asyncio.gather(listener, running, *owned, return_exceptions=True)
