"""Destinazione controllata solo per prove S03; non è una fonte del catalogo."""
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'controlled-target')

    def log_message(self,*args):
        pass


def udp():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
        server.bind(('0.0.0.0',53))
        while True:
            _,address=server.recvfrom(512)
            server.sendto(b'controlled-dns-response',address)


def tcp_dns():
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        server.bind(('0.0.0.0',53));server.listen()
        while True:
            connection,_=server.accept()
            connection.close()


if __name__=='__main__':
    threading.Thread(target=udp,daemon=True).start()
    threading.Thread(target=tcp_dns,daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',8088),Handler).serve_forever()
