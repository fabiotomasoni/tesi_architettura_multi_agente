"""Il long poll del ponte appartiene alla connessione HTTP che lo ha aperto."""
import asyncio
class DisconnectPollMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope.get('path')!='/_bridge/poll':
            return await self.app(scope,receive,send)
        incoming=asyncio.Queue(maxsize=2)
        async def watch():
            while True:
                message=await receive()
                await incoming.put(message)
                if message['type']=='http.disconnect':return
        handler=asyncio.create_task(self.app(scope,incoming.get,send))
        watcher=asyncio.create_task(watch())
        try:
            done,_=await asyncio.wait({handler,watcher},return_when=asyncio.FIRST_COMPLETED)
            if handler in done:return await handler
            handler.cancel()
            await asyncio.gather(handler,return_exceptions=True)
        finally:
            handler.cancel();watcher.cancel()
            await asyncio.gather(handler,watcher,return_exceptions=True)
