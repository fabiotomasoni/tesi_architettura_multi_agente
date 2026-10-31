"""Verifica S03 sullo stack Docker reale; output solo esiti e metadati."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
COMPOSE=['docker','compose','-f','compose.isolated.yaml','--profile','verification']


def run(arguments):
    result=subprocess.run(arguments,cwd=ROOT,text=True,capture_output=True,timeout=90)
    if result.returncode:
        raise RuntimeError('Comando di verifica non riuscito; controllare stato e log dei servizi.')
    return result.stdout


def execute(service, code):
    return json.loads(run(COMPOSE+['exec','-T',service,'python','-c',code]))


def guard_policy(info):
    guard=info['HostConfig']
    capabilities={cap.removeprefix('CAP_') for cap in (guard['CapAdd'] or [])}
    return (not guard['Privileged'] and guard['ReadonlyRootfs'] and guard['CapDrop']==['ALL']
            and capabilities=={'NET_ADMIN'} and 'no-new-privileges:true' in guard['SecurityOpt']
            and not any(m['Type']!='tmpfs' for m in info['Mounts']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/s03_isolation.json')
    args=parser.parse_args()
    deadline=time.monotonic()+30
    while True:
        try:
            response=httpx.get('http://127.0.0.1:8080/health',timeout=2,trust_env=False,follow_redirects=False)
            ready=response.status_code==200 and response.json().get('runtime_mode')=='isolated'
        except (httpx.HTTPError,ValueError):
            ready=False
        if ready:break
        if time.monotonic()>=deadline:
            raise RuntimeError('Gateway isolato non pronto entro 30 secondi; controllare lo stato dei container.')
        time.sleep(0.5)
    checks={};metadata={};probes={}
    # Controllo positivo: i bersagli vietati devono essere realmente raggiungibili
    # da un workload di controllo sulle stesse reti, altrimenti il diniego è inconcludente.
    control=execute('control',"import json;from services.isolation_probe import tcp,udp;print(json.dumps({n:tcp('172.30.'+n+'.4',8088) and tcp('172.30.'+n+'.4',53) and udp('172.30.'+n+'.4',53) for n in ('241','242')}))")
    checks['controlled_targets_available']=all(control.values())
    for role in ('gateway','markets','tax'):
        cid=run(COMPOSE+['ps','-q',role]).strip()
        if not cid:raise RuntimeError('Servizio applicativo assente')
        info=json.loads(run(['docker','inspect',cid]))[0]
        host=info['HostConfig']
        checks[role+'_non_privileged_config']=(info['Config']['User']=='10001:10001' and not host['Privileged'] and host['ReadonlyRootfs'] and host['CapDrop']==['ALL'] and not host['CapAdd'] and 'no-new-privileges:true' in host['SecurityOpt'])
        mounts=[m for m in info['Mounts'] if m['Type']!='tmpfs']
        checks[role+'_only_own_identity_mounted']=len(mounts)==1 and mounts[0]['Destination']=='/run/secrets/identity' and not mounts[0]['RW'] and Path(mounts[0]['Source']).name==role+'.json'
        metadata[role]={'image_id':info['Image'],'network_mode':host['NetworkMode']}
        probes[role]=execute(role,"import json;from services.isolation_probe import probe;print(json.dumps(probe('"+role+"')))")
        for key,value in probes[role].items():
            if value is not None:
                check_name=key.replace('_reachable','_blocked').replace('external_name_resolved','external_dns_blocked')
                checks[role+'_'+check_name]=(value if key in {'uid_non_root','no_effective_capabilities','runtime_socket_absent','dataset_absent'} else not value)
        if role!='gateway':
            data=json.loads(run(COMPOSE+['exec','-T',role,'python','-m','services.run_network_probe',role]).strip())
            probes[role+'_mcp']=data
            checks[role+'_mcp_no_outbound']=all(not value for key,value in data.items() if key.endswith('reachable') or key=='external_name_resolved')
            checks[role+'_mcp_unprivileged']=data['uid_non_root'] and data['no_effective_capabilities'] and data['runtime_socket_absent'] and data['dataset_absent']
    # Identità e percorso positivo controllati dentro la rete del gateway.
    auth=execute('gateway',"""
import json,httpx
from gateway.runtime import AGENT_ENDPOINTS
from gateway.identity import a2a_headers,HEADER,key_for
checks={}
with httpx.Client(timeout=5,trust_env=False,follow_redirects=False) as client:
 for scenario,endpoint in AGENT_ENDPOINTS.items():
  url=endpoint+'.well-known/agent-card.json'
  checks[scenario+'_card_authorized']=client.get(url,headers=a2a_headers(scenario)).status_code==200
  checks[scenario+'_card_no_key_denied']=client.get(url).status_code==403
  wrong='S-02' if scenario=='S-01' else 'S-01'
  checks[scenario+'_card_other_role_denied']=client.get(url,headers=a2a_headers(wrong)).status_code==403
print(json.dumps(checks))
""")
    checks.update(auth)
    for role,network in (('markets','241'),('tax','242')):
        result=execute(role,"""
import json,httpx
from gateway.identity import HEADER,key_for
role='"""+role+"""'
base='http://172.30."""+network+""".2:8000'
with httpx.Client(timeout=5,trust_env=False) as client:
 print(json.dumps({'gateway_reachable_and_auth_applied':client.post(base+'/internal/tools/authorize',json={},headers={HEADER:key_for(role+'_to_gateway',expected_role=role)}).status_code==422,
 'missing_identity_denied':client.post(base+'/internal/tools/authorize',json={}).status_code==403,
 'public_api_denied':client.get(base+'/health').status_code==403,
 'forwarded_headers_do_not_bypass':client.get(base+'/health',headers={'X-Forwarded-For':'127.0.0.1'}).status_code==403}))
""")
        checks.update({role+'_'+k:v for k,v in result.items()})
    # Gli agenti hanno solo reti interne. L'ingresso del gateway pubblica il solo
    # loopback host; il firewall del namespace vieta le nuove uscite da quella rete.
    for role in ('gateway','markets','tax'):
        cid=run(COMPOSE+['ps','-q','net-'+role]).strip()
        info=json.loads(run(['docker','inspect',cid]))[0]
        guard=info['HostConfig']
        checks[role+'_guard_restricted_config']=guard_policy(info)
        expected_ports={'8000/tcp':[{'HostIp':'127.0.0.1','HostPort':'8080'}]} if role=='gateway' else {}
        checks[role+'_only_expected_host_ports']=(guard.get('PortBindings') or {})==expected_ports
        networks=info['NetworkSettings']['Networks']
        expected_count=3 if role=='gateway' else 1
        details=[json.loads(run(['docker','network','inspect',n]))[0] for n in networks]
        checks[role+'_network_topology_verified']=len(networks)==expected_count and all(n['Internal'] or (role=='gateway' and n['Name']=='tesi-s03_ingress') for n in details) and sum(not n['Internal'] for n in details)==(1 if role=='gateway' else 0)
        rules=run(COMPOSE+['exec','-T','net-'+role,'iptables','-S'])
        ipv6=run(COMPOSE+['exec','-T','net-'+role,'ip6tables','-S'])
        checks[role+'_default_deny_ipv4_ipv6']=all('-P '+chain+' DROP' in table for table in (rules,ipv6) for chain in ('INPUT','OUTPUT','FORWARD'))
    result={'scope':'S03-local-Docker-workloads-and-live-MCP-probes','checks':checks,'probes':probes,'metadata':metadata,'passed':all(checks.values())}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for name,passed in checks.items():print(name+': '+str(passed))
    print('passed:',result['passed'])
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':
    try:main()
    except RuntimeError as error:raise SystemExit(str(error)) from None
