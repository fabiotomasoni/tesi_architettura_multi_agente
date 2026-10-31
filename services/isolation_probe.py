"""Sonde prive di dati personali: eseguibili anche all'interno di un tool MCP."""
import os
import socket
from pathlib import Path


def tcp(host,port):
    try:
        with socket.create_connection((host,port),timeout=0.7):return True
    except OSError:return False


def udp(host,port):
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as connection:
            connection.settimeout(0.7)
            connection.sendto(b's03-probe',(host,port))
            return bool(connection.recv(100))
    except OSError:return False


def probe(role):
    if role not in {'markets','tax','gateway'}:raise ValueError('Ruolo non ammesso')
    network='241' if role!='tax' else '242'
    target='172.30.'+network+'.4'
    gateway='172.30.'+network+'.2'
    capabilities=next(line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:'))
    try:
        socket.getaddrinfo('example.com',443)
        dns_resolved=True
    except OSError:dns_resolved=False
    return {'uid_non_root':os.geteuid()!=0, 'no_effective_capabilities':int(capabilities,16)==0,
            'runtime_socket_absent':not any(Path(p).exists() for p in ('/var/run/docker.sock','/run/docker.sock','/run/podman/podman.sock')),
            'dataset_absent':not Path('/app/dataset').exists(),
            'controlled_target_tcp_reachable':tcp(target,8088),
            'controlled_dns_udp_reachable':udp(target,53),
            'controlled_dns_tcp_reachable':tcp(target,53),
            'public_tcp_reachable':tcp('1.1.1.1',443),
            'external_name_resolved':dns_resolved,
            'other_agent_reachable':tcp('172.30.242.3' if role=='markets' else '172.30.241.3',8002 if role=='markets' else 8001) if role!='gateway' else None,
            'unconfigured_gateway_port_reachable':tcp(gateway,11434) if role!='gateway' else None}
