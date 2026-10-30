"""Pilota reale: richiede gateway, agente e Ollama già avviati."""
import argparse
import json
from pathlib import Path
from time import perf_counter
import platform
from importlib.metadata import version
import subprocess
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', default=['C001','C024','C006','C016'])
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('--output', default='runs/pilot.jsonl')
    parser.add_argument('--expect', choices=['nominal','agent-off','ollama-off','timeout'], default='nominal')
    parser.add_argument('--workflow', action='store_true', help='Usa LangGraph con chiusura automatica')
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 10: parser.error('Ripetizioni da 1 a 10')
    paths={}
    for case in args.cases:
        if case not in {f'C{i:03}' for i in range(1,26)}: parser.error('Caso non valido')
        paths[case]=ROOT/'dataset'/'Documents'/f'{case}_mutuo.pdf'
        if not paths[case].exists():parser.error('PDF del caso non disponibile')
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    git=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
    dirty=subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True)
    environment={'python':platform.python_version(),'google-adk':version('google-adk'),'a2a-sdk':version('a2a-sdk'),'mcp':version('mcp'),'langgraph':version('langgraph'),'commit':git.stdout.strip() if git.returncode==0 else 'uncommitted','working_tree_dirty':bool(dirty.stdout.strip()),'model_tag':'llama3.2:3b','num_ctx':4096,'temperature':0,'keep_alive':0}
    # Append: non sovrascrivere evidenze di prove precedenti.
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=135,trust_env=False) as client:
        for case,path in paths.items():
            for repetition in range(1,args.repetitions+1):
                sid=None
                expected=409 if case in {f'C{i:03}' for i in list(range(6,11))+list(range(16,21))} else 200
                if args.expect == 'agent-off': expected=502
                elif args.expect in {'ollama-off','timeout'}: expected=200
                row={'expectation':args.expect,'case':case,'repetition':repetition,'expected_http':expected,'environment':environment,'policy_version':'0.1.0','fixture':'simulated-rates-v1','cleanup_verified':False}
                started=perf_counter()
                try:
                    response=client.post('/sessions/pdf',files={'files':('input.pdf',path.read_bytes(),'application/pdf')},data={'scenarios':'S-01'})
                    response.raise_for_status();sid=response.json()['session_id'];row['policy_version']=response.json()['policy_version']
                    response=client.post(f'/sessions/{sid}/'+('workflow' if args.workflow else 'markets'))
                    row['http_status']=response.status_code
                    body=response.json()
                    row['workflow']=body.get('workflow')
                    row['phases']=body.get('phases',[])
                    row['automatic_session_closed']=body.get('session_closed',False)
                    row['status']=body.get('status','blocked' if response.status_code==409 else 'error')
                    row['measurements']=body.get('result',body).get('measurements',{})
                    row['error_code']=body.get('error_code')
                    desired=('failed' if args.workflow else 'error') if args.expect=='agent-off' else 'failed' if args.expect in {'ollama-off','timeout'} else 'blocked' if case in {f'C{i:03}' for i in list(range(6,11))+list(range(16,21))} else 'completed'
                    if args.workflow: expected=200
                    row['expected_http']=expected
                    row['passed']=response.status_code==expected and row['status']==desired and (args.expect!='timeout' or row['error_code']=='timeout')
                except httpx.HTTPError:
                    row.update(status='transport_error',passed=False)
                finally:
                    if sid:
                        try:
                            deleted=client.delete(f'/sessions/{sid}')
                            check=client.post(f'/sessions/{sid}/views',json={'scenario':'S-01','recipient':'markets'})
                            row['cleanup_verified']=deleted.status_code==(404 if args.workflow else 204) and check.status_code==404
                        except httpx.HTTPError:pass
                    row['elapsed_ms']=round((perf_counter()-started)*1000,3)
                    with output.open('a',encoding='utf-8') as file:file.write(json.dumps(row,ensure_ascii=False)+'\n')
                    print(case,repetition,row.get('http_status'),row['status'],'pulizia:',row['cleanup_verified'],flush=True)


if __name__=='__main__': main()
