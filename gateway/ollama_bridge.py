"""Coda volatile per inferenza locale: il ponte host ritira solo payload autorizzati."""
import asyncio
from copy import deepcopy
from dataclasses import dataclass
from secrets import token_hex


@dataclass
class Pending:
    payload: dict
    future: asyncio.Future
    claimed: bool = False


class OllamaBridge:
    def __init__(self):
        self.pending = {}
        self.queue = asyncio.Queue(maxsize=2)

    def purge_queue(self):
        live=[]
        while not self.queue.empty():
            job_id=self.queue.get_nowait()
            if job_id in self.pending:live.append(job_id)
        for job_id in live:self.queue.put_nowait(job_id)

    async def infer(self, payload, seconds):
        if len(self.pending) >= 2:
            raise RuntimeError('Budget del ponte esaurito')
        job_id = token_hex(32)
        future = asyncio.get_running_loop().create_future()
        self.pending[job_id] = Pending(deepcopy(payload), future)
        try:
            self.queue.put_nowait(job_id)
            async with asyncio.timeout(max(0, seconds)):
                return await future
        finally:
            self.pending.pop(job_id, None)
            self.purge_queue()
            if not future.done():
                future.cancel()

    async def poll(self):
        try:
            async with asyncio.timeout(15):
                while True:
                    job_id = await self.queue.get()
                    job = self.pending.get(job_id)
                    if job is not None and not job.claimed and not job.future.done():
                        job.claimed = True
                        return {'job_id': job_id, 'payload': deepcopy(job.payload)}
        except TimeoutError:
            return None

    def kind(self, job_id):
        job=self.pending.get(job_id)
        return job.payload.get('kind','inference') if job is not None else None

    def complete(self, job_id, *, body=None, error=None, ollama_ms=None, source_ms=None):
        job = self.pending.get(job_id)
        if job is None or not job.claimed or job.future.done():
            return False
        if error:
            job.future.set_exception(TimeoutError('Timeout del ponte') if error == 'timeout'
                                     else RuntimeError('Inferenza del ponte non completata'))
        else:
            reply={'body':body,'ollama_ms':ollama_ms}
            if source_ms is not None:reply['source_ms']=source_ms
            job.future.set_result(reply)
        return True

    def close(self):
        for job in self.pending.values():
            if not job.future.done():
                job.future.set_exception(RuntimeError('Ponte arrestato'))
        self.pending.clear()
