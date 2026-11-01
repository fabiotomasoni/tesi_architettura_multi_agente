"""Controlli descrittivi delle quattro celle pilota; non giudizio umano o campagna finale."""
import argparse,json
from pathlib import Path
if __package__ in (None,''):
    from check_baseline_pilot import verify as pair_verify
else:
    from .check_baseline_pilot import verify as pair_verify


def verify(cells):
    checks={};indexed={}
    expected={('single','active'),('multi','active'),('single','disabled'),('multi','disabled')}
    if set(cells)!=expected:return {'four_cells_present':False}
    for (organization,policy),rows in cells.items():
        records={}
        for r in rows:
            key=(r['case'],r['repetition'])
            if key in records:raise ValueError('Righe duplicate')
            records[key]=r
            if r.get('minimization')!=policy or r['experiment']['policy']!=policy or r['experiment'].get('protocol')!='financial-profile-2x2-v1':raise ValueError('Profili o protocolli diversi: rieseguire i quattro piloti')
        indexed[organization,policy]=records
    keys=set(indexed['single','active'])
    checks['same_cases_and_repetitions']=bool(keys) and all(set(x)==keys for x in indexed.values())
    for policy in ('active','disabled'):
        for k,v in pair_verify(cells['single',policy],cells['multi',policy]).items():checks[policy+'/'+k]=v
    for organization in ('single','multi'):
        for key in sorted(keys):
            if key not in indexed[organization,'disabled']:continue
            a=indexed[organization,'active'][key];b=indexed[organization,'disabled'][key];label=organization+'/'+key[0]+'/'+str(key[1])
            x={k:v for k,v in a['experiment'].items() if k not in {'policy'}};y={k:v for k,v in b['experiment'].items() if k not in {'policy'}}
            checks[label+'/same_other_settings']=x==y and a['model_digest']==b['model_digest']
            checks[label+'/same_structured_result']=a['semantic_result_sha256']==b['semantic_result_sha256']
            for scenario in ('S-01','S-02'):
                if a['activities'][scenario]['status']!='completed':continue
                am=a['activities'][scenario]['measurements'];bm=b['activities'][scenario]['measurements']
                for boundary in ('a2a_view','mcp_arguments','model_context'):
                    checks[label+'/'+scenario+'/'+boundary+'_larger']=bm.get(boundary+'_bytes',0)>am.get(boundary+'_bytes',0)
                    checks[label+'/'+scenario+'/'+boundary+'_no_exact_amounts_with_policy']=am.get(boundary+'_exact_amount_fields')==0
                    checks[label+'/'+scenario+'/'+boundary+'_exact_amounts_without_policy']=bm.get(boundary+'_exact_amount_fields')==b['input_financial_amount_fields'] and b['input_financial_amount_fields']>0
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('single-active','multi-active','single-disabled','multi-disabled'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    try:
        cells={(o,m):[json.loads(l) for l in getattr(a,o+'_'+m).read_text().splitlines() if l.strip()] for o in ('single','multi') for m in ('active','disabled')}
        checks=verify(cells)
    except (ValueError,KeyError,TypeError) as e:raise SystemExit('Confronto non valido: '+str(e))
    for k,v in checks.items():print(k+': '+str(bool(v)))
    print('passed:',all(checks.values()))
    raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
