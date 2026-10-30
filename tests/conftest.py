"""Server temporaneo esclusivamente loopback per callback dei sottoprocessi MCP."""
from contextlib import contextmanager
import socket
import threading
import time
import pytest
import uvicorn


@pytest.fixture
def local_gateway():
    @contextmanager
    def serve(app):
        sock=socket.socket(); sock.bind(('127.0.0.1',0)); sock.listen(128)
        port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='critical',access_log=False))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True)
        thread.start()
        try:
            until=time.monotonic()+5
            while not server.started:
                if not thread.is_alive() or time.monotonic()>until:raise RuntimeError('Gateway di test non avviato')
                time.sleep(0.01)
            yield f'http://127.0.0.1:{port}'
        finally:
            server.should_exit=True;thread.join(5);sock.close()
            assert not thread.is_alive()
    return serve
