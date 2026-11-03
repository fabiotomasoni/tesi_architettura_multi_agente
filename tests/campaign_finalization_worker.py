"""TTL/guasto ASGI: riusa il collaudo nativo, senza fingere isolamento Docker."""
import argparse,os,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--block',required=True);a=p.parse_args()
    from scripts.campaign_support import Collector,read,write_new
    block=next(b for b in read(a.directory.parent/'pilot_plan.json' if a.directory.name=='pilot' else a.directory.parent/'plan.json')['blocks'] if b['id']==a.block)
    org,policy=block['cell'].split('-')
    os.environ.update(TESI_RUNTIME='local',TESI_EXPERIMENT=org,TESI_MINIMIZATION=policy,TESI_SHARED_REFERENCE='1',TESI_VERIFICATION_PROFILE='nominal',TESI_MARKET_SOURCE='simulated',TESI_TAX_SOURCE='simulated',TESI_MCP_PROFILE='nominal',TESI_MARKET_TOOL_IMPLEMENTATION='standard')
    import tests.block2_worker as lab
    from contextlib import ExitStack
    from fastapi.testclient import TestClient
    collector=Collector(a.directory,block,'native');passed=False
    def hook(response):
        response.read()
        try:body=response.json()
        except ValueError:body={}
        collector.capture(response.request.method,response.request.url.path,response.status_code,body,response.headers.get('x-trace-id'))
    try:
        with ExitStack() as stack:
            for agent in {id(x):x for x in lab.agents.values()}.values():stack.enter_context(TestClient(agent))
            stack.enter_context(lab.serve());client=stack.enter_context(TestClient(lab.app))
            client.event_hooks['response']=[hook]
            def variant(name):collector.context={'case':'C001','variant':name}
            lab.finalization_checks(client,faults=('ttl','delivery_asgi'),before_each=True,on_variant=variant)
            passed=True
    finally:
        rows=collector.finish(procedure_passed=passed)
        write_new(a.directory/'private/native'/(a.block+'.json'),{'passed':passed,'rows':rows})
    raise SystemExit(0 if passed else 1)
if __name__=='__main__':main()
