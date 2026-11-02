"""Pilota 2x2 locale, metadati senza contenuti documentali; non campagna finale."""
import argparse,hashlib,json
from pathlib import Path
from importlib.metadata import version
import httpx
if __package__:
    from .trace_export import record_trace
else:
    from trace_export import record_trace

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--organization',choices=['single','multi'],required=True)
    p.add_argument('--minimization',choices=['active','disabled'],default='active')
    p.add_argument('--cases',nargs='+',default=['C001','C024','C006','C011','C016'])
    p.add_argument('--repetitions',type=int,default=1)
    p.add_argument('--gateway-url',choices=['http://127.0.0.1:8080','http://127.0.0.1:8081'],default='http://127.0.0.1:8080')
    p.add_argument('--output',required=True)
    a=p.parse_args()
    if not 1<=a.repetitions<=3 or any(c not in {f'C{i:03}' for i in range(1,26)} for c in a.cases):p.error('Casi C001–C025 e da 1 a 3 ripetizioni per il solo pilota')
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    tags=httpx.get('http://127.0.0.1:11434/api/tags',trust_env=False,timeout=10);tags.raise_for_status()
    digest=next((m['digest'] for m in tags.json()['models'] if m['name']=='llama3.2:3b'),None)
    if not digest:raise SystemExit('Modello llama3.2:3b non disponibile in Ollama.')
    with httpx.Client(base_url=a.gateway_url,timeout=135,trust_env=False) as c:
        h=c.get('/health');h.raise_for_status();health=h.json()
        if health.get('experiment')!=a.organization or health.get('minimization')!=a.minimization or health.get('runtime_mode')!='isolated' or any(health.get(k)!='simulated' for k in ('market_source','tax_source')):
            raise SystemExit('Gateway non configurato per questo profilo sperimentale. Nessun PDF inviato.')
        for case in a.cases:
            for repetition in range(1,a.repetitions+1):
                sid=None;trace_identifier=None;row={'scope':'baseline_pilot_not_final_campaign','case':case,'repetition':repetition,'organization':a.organization,'minimization':a.minimization,'model_digest':digest,'langgraph':version('langgraph'),'cleanup_verified':False}
                try:
                    files=[('files',(k+'.pdf',(ROOT/'dataset/Documents'/f'{case}_{k}.pdf').read_bytes(),'application/pdf')) for k in ('mutuo','interessi')]
                    r=c.post('/sessions/pdf',files=files,data={'scenarios':['S-01','S-02']});r.raise_for_status();sid=r.json()['session_id'];trace_identifier=r.json().get('trace_id')
                    row['input_financial_amount_fields']=sum(r.json()['profile'].get(k) is not None for k in ('remaining_principal','payment_amount','annual_interest'))
                    r=c.post(f'/sessions/{sid}/analysis');r.raise_for_status();body=r.json()
                    n=int(case[1:]);expected={'S-01':'blocked' if 6<=n<=10 or 16<=n<=20 else 'completed','S-02':'blocked' if 11<=n<=15 else 'completed'}
                    activities={s:{'status':x['status'],'error_code':x.get('error_code'),'phases':x['phases'],'model':(x.get('result') or {}).get('model'),'measurements':(x.get('result') or {}).get('measurements',{})} for s,x in body['activities'].items()}
                    report=body['report']
                    if __package__ in (None,''):
                        from check_mortgage import verify as mortgage
                        from check_tax_application import verify as tax
                    else:
                        from .check_mortgage import verify as mortgage
                        from .check_tax_application import verify as tax
                    checks={**mortgage(report),**tax(report)}
                    # Nessun dato della fixture o contenuto del report viene archiviato.
                    stable={'status':report['status'],'mortgage':report['mortgage_comparison'],'contract':report.get('mortgage_contract_analysis'),'tax':report['tax_application']}
                    signature=hashlib.sha256(json.dumps(stable,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                    models_match=all((x.get('result') or {}).get('model')=='llama3.2:3b' for x in body['activities'].values() if x['status']=='completed')
                    row.update(status=body['status'],experiment=body['experiment'],coordination=body.get('coordination_measurements',{}),activities=activities,total_ms=body['total_ms'],report_ms=body['report_ms'],cleanup_ms=body['cleanup_ms'],automatic_session_closed=body['session_closed'],report_checks=checks,semantic_result_sha256=signature,passed=models_match and all(checks.values()) and all(activities[s]['status']==v for s,v in expected.items()))
                except (httpx.HTTPError,KeyError,ValueError):row.update(status='error',passed=False)
                finally:
                    record_trace(c,row,trace_identifier,organization=a.organization,minimization=a.minimization)
                    row['passed']=row.get('passed',False) and row['trace_verified']
                    if sid:
                        try:row['cleanup_verified']=c.delete(f'/sessions/{sid}').status_code==404
                        except httpx.HTTPError:pass
                    with output.open('a') as f:f.write(json.dumps(row)+'\n')
                    print(case,repetition,row['status'],'passed:',row['passed'],'pulizia:',row['cleanup_verified'],flush=True)


if __name__=='__main__':main()
