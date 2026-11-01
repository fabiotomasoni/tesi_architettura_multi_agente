"""Confronto descrittivo del pilota S+P/M+P: nessuna conclusione statistica."""
import argparse,json
from pathlib import Path


def verify(single,multi):
    def indexed(rows,organization):
        result={}
        for r in rows:
            key=(r['case'],r['repetition'])
            if key in result or r['organization']!=organization:raise ValueError('Righe duplicate o organizzazione errata: usare file nuovi')
            result[key]=r
        return result
    s=indexed(single,'single');m=indexed(multi,'multi')
    checks={'same_cases_and_repetitions':bool(s) and set(s)==set(m)}
    for key in sorted(set(s)&set(m)):
        a,b=s[key],m[key];label=key[0]+'/'+str(key[1])
        checks[label+'/runs_passed']=all(r.get('passed') and r.get('cleanup_verified') and r.get('automatic_session_closed') for r in (a,b))
        checks[label+'/same_weights']=a.get('model_digest')==b.get('model_digest') and bool(a.get('model_digest'))
        x={k:v for k,v in a['experiment'].items() if k!='organization'};y={k:v for k,v in b['experiment'].items() if k!='organization'}
        checks[label+'/same_settings']=x==y and x['sources']=='fixed_local_fixtures' and x['policy']=='active' and x['schedule']=='sequential'
        checks[label+'/same_structured_result']=a['semantic_result_sha256']==b['semantic_result_sha256']
        for r,kind in ((a,'single'),(b,'multi')):
            activities=r['activities'];completed=[v['measurements'] for v in activities.values() if v['status']=='completed']
            sends=r.get('coordination',{}).get('a2a_message_sends',0) if kind=='single' else sum(v['measurements'].get('a2a_requests',0) for v in activities.values())
            checks[label+'/'+kind+'_delegations']=sends==(1 if completed and kind=='single' else len(completed))
            checks[label+'/'+kind+'_calls']=sum(v.get('mcp_tool_calls',0) for v in completed)==len(completed) and sum(v.get('ollama_calls',0) for v in completed)==len(completed)
            boots={v.get('agent_boot_id') for v in completed}
            checks[label+'/'+kind+'_agent_identity']=len(boots)==(1 if kind=='single' and completed else len(completed)) and None not in boots
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('single',type=Path);p.add_argument('multi',type=Path);a=p.parse_args()
    try:checks=verify([json.loads(x) for x in a.single.read_text().splitlines() if x.strip()],[json.loads(x) for x in a.multi.read_text().splitlines() if x.strip()])
    except (ValueError,KeyError,TypeError) as e:raise SystemExit('File non confrontabili: '+str(e))
    for k,v in checks.items():print(k+': '+str(bool(v)))
    print('passed:',all(checks.values()))
    raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
