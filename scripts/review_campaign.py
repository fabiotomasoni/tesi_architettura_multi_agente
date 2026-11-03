"""Esportazione cieca e riepiloghi: i voti sono inseriti soltanto dal valutatore."""
import argparse,csv,json,random,sys
from collections import defaultdict,Counter
from hashlib import sha256
from html import escape
from pathlib import Path
from uuid import uuid4
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.campaign_support import ROOT,read,write_new,digest,blind,describe,REVIEW_COLUMNS,verify_bundle,verify_results
from scripts.evaluation_support import quality_score


def rows_for(folder):
    rows=[]
    for path in sorted((Path(folder)/'private/blocks').glob('*.json')):rows.extend(read(path)['rows'])
    if len({r['run_id'] for r in rows})!=len(rows):raise ValueError('ID di esecuzione duplicati.')
    return rows


def export_review(folder):
    folder=Path(folder);rows=rows_for(folder)
    if not rows:raise ValueError('Nessuna esecuzione raccolta: non si creano voti o report fittizi.')
    if (folder/'public').exists():raise ValueError('Registro pubblico già presente: non sovrascriverlo.')
    selected=[r for r in rows if r['report_delivered']]
    random.SystemRandom().shuffle(selected);mapping=[];ratings=[]
    from gateway.report_document import render_report_document
    css=(ROOT/'gateway/static/app.css').read_text(encoding='utf-8')
    for row in selected:
        original=read(folder/row['report_path'])
        if digest(original)!=row['report_sha256']:raise ValueError('Report originale modificato.')
        evaluation_id='E-'+uuid4().hex;report=blind(original);report_sha=digest(report)
        name='reports/'+evaluation_id
        html='<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Report da valutare</title><style>'+css+'</style></head><body><main>'+render_report_document(report)+'</main></body></html>'
        write_new(folder/'public'/(name+'.json'),report)
        (folder/'public'/(name+'.html')).write_text(html,encoding='utf-8')
        mapping.append({'evaluation_id':evaluation_id,'run_id':row['run_id'],'case_id':row['case'],
                        'report_sha256':report_sha,'html_sha256':sha256(html.encode()).hexdigest(),
                        'original_report_sha256':row['report_sha256']})
        ratings.append({'evaluation_id':evaluation_id,'case_id':row['case'],'report_sha256':report_sha,**{k:'' for k in REVIEW_COLUMNS[3:]}})
    with (folder/'public/ratings.csv').open('x',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=REVIEW_COLUMNS);writer.writeheader();writer.writerows(ratings)
    links=''.join('<li>'+escape(r['case_id'])+' — <a href="reports/'+r['evaluation_id']+'.html">'+r['evaluation_id']+'</a></li>' for r in ratings)
    (folder/'public/index.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><title>Valutazione dei report</title><h1>Report da valutare</h1><p>Un valutatore. Compilare ratings.csv: correttezza, copertura, provenienza e limiti da 0 a 2; critical_error yes/no. Nessun voto è precompilato. Confrontare i dati con i PDF del caso nel dataset locale. Non consultare il registro privato durante la valutazione. Il contenuto può comunque suggerire la condizione: cecità limitata, nessuna stima di accordo tra valutatori.</p><ol>'+links+'</ol></html>',encoding='utf-8')
    write_new(folder/'private/review_mapping.json',{'entries':mapping,'absent_reports':[{'run_id':r['run_id'],'reason':r.get('absence_reason',r['status'])} for r in rows if not r['report_delivered']]})
    return len(mapping)


def read_ratings(folder,path):
    folder=Path(folder);mapping=read(folder/'private/review_mapping.json')['entries']
    delivered={r['run_id']:r for r in rows_for(folder) if r['report_delivered']}
    if len(mapping)!=len(delivered) or {r['run_id'] for r in mapping}!=set(delivered):raise ValueError('Registro cieco non corrispondente ai report consegnati.')
    expected={r['evaluation_id']:r for r in mapping};result={};seen=set()
    with Path(path).open(encoding='utf-8-sig',newline='') as file:
        reader=csv.DictReader(file)
        if reader.fieldnames!=REVIEW_COLUMNS:raise ValueError('Colonne del registro modificate.')
        for row in reader:
            if set(row)!=set(REVIEW_COLUMNS) or any(value is None for value in row.values()):raise ValueError('Riga CSV incompleta o con colonne aggiuntive.')
            key=row['evaluation_id'];record=expected.get(key)
            if record is None or key in seen:raise ValueError('ID sconosciuto o duplicato nella valutazione.')
            if any(row[k]!=record[k] for k in ('case_id','report_sha256')):raise ValueError('Caso o impronta del report modificati.')
            original=read(folder/delivered[record['run_id']]['report_path'])
            if digest(original)!=record['original_report_sha256'] or digest(blind(original))!=record['report_sha256']:raise ValueError('Legame con il report originale non valido.')
            report=read(folder/'public/reports'/(key+'.json'))
            html=(folder/'public/reports'/(key+'.html')).read_bytes()
            if digest(report)!=record['report_sha256'] or sha256(html).hexdigest()!=record['html_sha256']:raise ValueError('Documento valutato modificato.')
            result[record['run_id']]=quality_score(row);seen.add(key)
    if len(result)!=len(expected):raise ValueError('Valutazioni mancanti; nessun completamento automatico.')
    return result


def interval_union(spans):
    if any(s.get('duration_ms') is None for s in spans):return None
    total=end=0
    for left,right in sorted((s['start_ms'],s['start_ms']+s['duration_ms']) for s in spans):
        total+=max(0,right-max(end,left));end=max(end,right)
    return total


def summarize(rows, ratings=None):
    ratings=ratings or {};groups=defaultdict(list)
    for row in rows:
        # Controlli adiacenti distinti: non diventano repliche indipendenti.
        slot=row['run_id'].rsplit('-',1)[-1] if row['kind']!='base' else 'base'
        groups[(row['kind'],row['cell'],row['case'],row['variant'],slot)].append(row)
    result=[]
    metrics=('total_ms','report_ms','cleanup_ms','prompt_tokens','output_tokens','backend_request_union_ms','a2a_message_dispatch_attempts','mcp_tool_calls_agent_reported','model_proxy_calls','host_http_dispatch_attempts')
    for (kind,cell,case,variant,slot),records in sorted(groups.items()):
        values={key:[] for key in metrics};qualities=[];utilities=defaultdict(list);phases=defaultdict(list);disclosures=defaultdict(list)
        for row in records:
            trace=row.get('trace') or {};summary=trace.get('summary') or {}
            for key in metrics:values[key].append(row.get(key) if key in {'total_ms','report_ms','cleanup_ms'} else summary.get(key))
            qualities.append((ratings.get(row['run_id']) or {}).get('total'))
            for s in ('S-01','S-02'):utilities[s].append(row.get('utility',{}).get(s,{}).get('ratio'))
            for scenario,measurements in row.get('disclosure',{}).items():
                for key,value in measurements.items():disclosures[scenario+'/'+key].append(value)
            observed={s['phase'] for s in trace.get('spans',[])}
            for phase in observed:phases[phase].append(interval_union([s for s in trace['spans'] if s['phase']==phase]))
        result.append({'kind':kind,'expected_model_mode':'actual_local_ollama' if kind=='base' else 'controlled_not_actual_ollama','observed_model_modes':dict(Counter(r.get('model_mode','unconfirmed') for r in records)),
                       'cell':cell,'case':case,'variant':variant,'control_slot':slot,
                       'attempts':len(records),'independent_repetitions':len({r['repetition'] for r in records}),
                       'statuses':dict(Counter(r['status'] for r in records)),
                       'technical_passes':sum(r.get('passed') is True for r in records),'technical_assertions_unknown':sum('passed' not in r for r in records),
                       'cleanup_confirmed':sum(r.get('cleanup_verified') is True for r in records),
                       'metrics':{k:describe(v) for k,v in values.items()},'quality':describe(qualities),
                       'utility':{s:describe(v) for s,v in utilities.items()},
                       'phase_union_ms':{p:describe(v+[None]*(len(records)-len(v))) for p,v in phases.items()},
                       'disclosure':{k:describe(v+[None]*(len(records)-len(v))) for k,v in disclosures.items()},'observed_money_EUR':None})
    # Contrasti appaiati per caso/ripetizione; mai aggregare controlli con le basi.
    base={(r['cell'],r['case'],r['repetition']):r for r in rows if r['kind']=='base'}
    if len(base)!=sum(r['kind']=='base' for r in rows):raise ValueError('Caso/cella/ripetizione duplicati.')
    contrasts=[]
    for org in ('single','multi'):
        for case in sorted({r['case'] for r in rows if r['kind']=='base'}):
            loss={'S-01':[],'S-02':[]};quality_loss=[]
            for rep in range(1,11):
                a=base.get((org+'-active',case,rep));b=base.get((org+'-disabled',case,rep))
                if not a or not b:continue
                score_a=ratings.get(a['run_id']);score_b=ratings.get(b['run_id'])
                quality_loss.append(score_b['total']-score_a['total'] if score_a and score_b else None)
                for s in ('S-01','S-02'):
                    u=a.get('utility',{}).get(s,{}).get('ratio');v=b.get('utility',{}).get(s,{}).get('ratio')
                    loss[s].append(v-u if u is not None and v is not None else None)
            contrasts.append({'organization':org,'case':case,'quality_loss_without_minus_with_policy':describe(quality_loss),'utility_loss_without_minus_with_policy':{s:describe(v) for s,v in loss.items()}})
    effects=[];interactions=[]
    def measured(row,key):
        if row is None:return None
        if key=='quality':return (ratings.get(row['run_id']) or {}).get('total')
        return row.get('total_ms') if key=='total_ms' else (row.get('trace') or {}).get('summary',{}).get(key)
    for case in sorted({r['case'] for r in rows if r['kind']=='base'}):
        repetitions=sorted({r['repetition'] for r in rows if r['kind']=='base' and r['case']==case})
        for metric in ('total_ms','prompt_tokens','output_tokens','quality'):
            effect={p:[] for p in ('active','disabled')};interaction=[]
            for rep in repetitions:
                differences={}
                for policy in effect:
                    single=measured(base.get(('single-'+policy,case,rep)),metric);multi=measured(base.get(('multi-'+policy,case,rep)),metric)
                    delta=multi-single if multi is not None and single is not None else None
                    effect[policy].append(delta);differences[policy]=delta
                interaction.append(differences['active']-differences['disabled'] if all(v is not None for v in differences.values()) else None)
            effects.append({'case':case,'metric':metric,'multi_minus_single':{p:describe(v) for p,v in effect.items()}})
            interactions.append({'case':case,'metric':metric,'organization_effect_with_policy_minus_without_policy':describe(interaction)})
    return {'scope':'descriptive_not_claim_of_superiority','groups':result,'privacy_utility_contrasts':contrasts,'organization_contrasts':effects,'interaction_contrasts':interactions,
            'quality_rated':len(ratings),'individual_quality_thresholds_satisfied':all(s['meets_individual_thresholds'] for s in ratings.values()) if ratings else None,
            'observed_unauthorized_transmissions':None,'required_unauthorized_transmissions':0,
            'privacy_interpretation':'Use isolation and scoped payload/endpoint checks. Missing observations are not zero violations; denials are not disclosures.',
            'disclosure_interpretation':'Canonical JSON bytes and field categories, not wire bytes; authorized exact financial fields in -P are not violations.',
            'cost_interpretation':'No API prices or unmeasured electricity/hardware costs asserted. Controlled tokens are separated from actual Ollama usage.',
            'timing_interpretation':'Nested phases are inclusive; within each phase use interval union, never sum all phase durations.',
            'threshold_interpretation':'The individual-quality flag covers the per-report rubric only; relative loss and the zero-violation constraint require separate assessment.',
            'human_interpretation':'One evaluator; no inter-rater agreement; absence is not assigned zero; quality missing until CSV completed.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['export','summary']);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--pilot',action='store_true');p.add_argument('--ratings',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        errors=verify_bundle(a.directory)
        if errors:raise ValueError('Manifest modificato: '+', '.join(errors))
        folder=a.directory/('pilot' if a.pilot else 'final')
        if (folder/'completion.json').exists() and verify_results(a.directory,pilot=a.pilot):raise ValueError('Evidenze raccolte modificate.')
        if a.action=='export':print('Report consegnati da valutare:',export_review(folder));print('Punteggi assegnati automaticamente: 0')
        else:
            if not a.output:raise ValueError('Specificare un file --output nuovo.')
            scores=read_ratings(folder,a.ratings) if a.ratings else None
            summary=summarize(rows_for(folder),scores)
            summary['manifest_sha256']=digest(read(a.directory/'manifest.json'));summary['pilot']=a.pilot;summary['collection_complete']=(folder/'completion.json').exists();summary['collection_technical_passed']=read(folder/'completion.json')['passed'] if (folder/'completion.json').exists() else None
            write_new(a.output,summary);print('Valutazioni umane presenti:',summary['quality_rated']);print('Riepilogo descrittivo salvato.')
    except (ValueError,KeyError,OSError) as e:p.error(str(e))
if __name__=='__main__':main()
