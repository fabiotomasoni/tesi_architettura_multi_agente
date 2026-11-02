"""Pilota con due specialisti, fonti simulate e chiusura automatica."""
import argparse,json
from pathlib import Path
from importlib.metadata import version
import httpx

if __package__:
    from .trace_export import record_trace
else:
    from trace_export import record_trace

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',nargs='+',default=['C001','C024','C006','C011','C016'])
    parser.add_argument('--scenarios',nargs='+',choices=['S-01','S-02'],default=['S-01','S-02'])
    parser.add_argument('--repetitions',type=int,default=1)
    parser.add_argument('--gateway-url',choices=['http://127.0.0.1:8000','http://127.0.0.1:8080'],default='http://127.0.0.1:8000')
    parser.add_argument('--output',default='runs/multi_pilot.jsonl')
    args=parser.parse_args()
    if not 1<=args.repetitions<=10:parser.error('Ripetizioni da 1 a 10')
    if any(c not in {f'C{i:03}' for i in range(1,26)} for c in args.cases):parser.error('Caso non valido')
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    with httpx.Client(base_url=args.gateway_url,timeout=135,trust_env=False) as client:
        for case in args.cases:
            for repetition in range(1,args.repetitions+1):
                sid=None;trace_identifier=None
                row={'case':case,'repetition':repetition,'policy_version':'0.2.0','workflow':'multi-langgraph-v1','langgraph':version('langgraph'),'scenarios':args.scenarios,'cleanup_verified':False}
                try:
                    files=[('files',(kind+'.pdf',(ROOT/'dataset'/'Documents'/f'{case}_{kind}.pdf').read_bytes(),'application/pdf')) for kind in ['mutuo','interessi']]
                    response=client.post('/sessions/pdf',files=files,data={'scenarios':args.scenarios});response.raise_for_status()
                    sid=response.json()['session_id'];trace_identifier=response.json().get('trace_id');row['policy_version']=response.json()['policy_version']
                    response=client.post(f'/sessions/{sid}/analysis');response.raise_for_status()
                    body=response.json()
                    # Esportare solo metadati, senza sintesi o contenuto fiscale.
                    activities={s:{'status':r['status'],'error_code':r.get('error_code'),'phases':r['phases'],'measurements':r.get('result',{}).get('measurements',{})} for s,r in body['activities'].items()}
                    n=int(case[1:]);expected={s:('blocked' if (s=='S-01' and (6<=n<=10 or 16<=n<=20)) or (s=='S-02' and 11<=n<=15) else 'completed') for s in args.scenarios}
                    row.update(report_present=body.get('report') is not None,report_ms=body.get('report_ms'),status=body['status'],activities=activities,total_ms=body['total_ms'],automatic_session_closed=body['session_closed'],passed=set(activities)==set(expected) and all(activities[s]['status']==v for s,v in expected.items()))
                except httpx.HTTPError:row.update(status='transport_error',passed=False)
                finally:
                    record_trace(client,row,trace_identifier)
                    row['passed']=row.get('passed',False) and row['trace_verified']
                    if sid:
                        try:row['cleanup_verified']=client.delete(f'/sessions/{sid}').status_code==404
                        except httpx.HTTPError:pass
                    with output.open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
                    print(case,repetition,row['status'],'passed:',row['passed'],'pulizia:',row['cleanup_verified'],flush=True)

if __name__=='__main__':main()
