"""Verifica la bozza del valutatore; non approva soglie e non esegue la campagna."""
import argparse,ast,csv,hashlib,json,re
from decimal import Decimal
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]


def annotation_checks(annotation,directory):
    checks={'case_count':annotation.get('case_count')==25 and len(annotation.get('cases',[]))==25,
        'reference_status_known':annotation.get('status') in {'draft_pending_human_review','human_reviewed'}}
    cases=annotation.get('cases',[])
    checks['unique_cases']={c['case_id'] for c in cases}=={f'C{i:03}' for i in range(1,26)}
    labels={'rate_type':'Tipo tasso','remaining_principal':'Capitale residuo','remaining_months':'Durata residua','annual_rate':'Tasso annuo nominale','payment_amount':'Rata mensile','tax_year':'Anno imposta','purpose':'Finalita','annual_interest':'Interessi annui documentati','ownership_share':'Quota intestazione'}
    allowed=set(labels)|{'payment_frequency','mortgage_type'}
    for case in cases:
        cid=case['case_id'];checks[cid+'/fact_inventory']=set(case['facts'])==allowed
        for name,digest in case['pdf_sha256'].items():
            if Path(name).name!=name:raise ValueError('Nome PDF fuori catalogo')
            checks[cid+'/pdf/'+name]=hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest
        texts={s:'\n'.join(p.extract_text() for p in PdfReader(directory/(cid+'_'+kind+'.pdf')).pages) for s,kind in [('S-01','mutuo'),('S-02','interessi')]}
        match=re.search(r'Situazione al (\d{2})/(\d{2})/(\d{4})',texts['S-01'])
        d,m,y=match.groups();contract_period=f'{y}-{m}-{d}'
        tax_lines=[x.strip() for x in texts['S-02'].splitlines()];tax_period=tax_lines[tax_lines.index('Anno imposta')+1]+'-12-31'
        units={'rate_type':'category','remaining_principal':'EUR','remaining_months':'month','annual_rate':'percent_per_year','payment_amount':'EUR','tax_year':'year','purpose':'category','annual_interest':'EUR','ownership_share':'fraction','payment_frequency':'category','mortgage_type':'category'}
        for key,fact in case['facts'].items():
            checks[cid+'/'+key+'/unit_and_period']=fact['unit']==units[key] and fact['period']==(contract_period if fact['scenario']=='S-01' else tax_period)
            checks[cid+'/'+key+'/no_latent_value']=fact['status']=='validated' or fact['value'] is None
            if key not in labels:continue
            lines=[s.strip() for s in texts[fact['scenario']].splitlines()]
            label=labels[key];indices=[i for i,line in enumerate(lines) if line==label]
            if fact['status']=='missing':checks[cid+'/'+key+'/missing']=not indices;continue
            if len(indices)!=1:checks[cid+'/'+key+'/label']=False;continue
            raw=lines[indices[0]+1]
            if fact['status']=='ambiguous':
                checks[cid+'/'+key+'/ambiguous']=len(re.findall(r'\d+(?:[.,]\d+)?\s*%',raw))>1
                continue
            if key in {'rate_type','purpose'}:
                mapping={'fisso':'fixed','variabile':'variable','misto':'mixed','acquisto abitazione principale':'primary_home_purchase','ristrutturazione':'renovation','costruzione abitazione principale':'primary_home_construction'}
                checks[cid+'/'+key+'/value']=mapping.get(raw.strip(),raw.strip())==fact['value']
            else:
                value=Decimal(raw.replace('EUR','').replace('mesi','').replace('%','').strip().replace('.','').replace(',','.'))
                if key=='ownership_share':value/=100
                checks[cid+'/'+key+'/value']=value==Decimal(fact['value'])
    return checks


def review_checks(review,annotations):
    cases={c['case_id']:c for c in annotations['cases']}
    confirmed=review.get('confirmed_cases',{})
    complete=review.get('status')=='complete'
    checks={'review/scope':review.get('status') in {'partial','complete'} and review.get('reviewed_by')=='user' and review.get('scope')=='pdf_annotation_reference_only_not_report_quality_or_campaign',
            'review/version':review.get('annotation_version')==annotations['annotation_version'],
            'review/coverage':set(confirmed)==set(cases) if complete else bool(confirmed) and set(confirmed)<set(cases),
            'review/reference_status':annotations.get('status')==('human_reviewed' if complete else 'draft_pending_human_review')}
    for cid,digest in confirmed.items():
        current=hashlib.sha256(json.dumps(cases.get(cid),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        checks['review/'+cid+'/reference_unchanged']=cid in cases and digest==current
    return checks


def verify(protocol,annotations,root=ROOT):
    complete=protocol.get('annotation_review',{}).get('status')=='complete'
    expected_status='draft_pending_verification' if complete else 'draft_pending_annotation_review_and_verification'
    checks={'draft_not_frozen':protocol.get('status')==expected_status and protocol.get('approved_by') is None and protocol.get('frozen_at') is None,
            'annotation_review_gate_consistent':('human_review_of_annotations' not in protocol['freeze_blockers'])==complete,
            'single_human_evaluator':protocol['evaluators']['count']==1 and protocol['evaluators']['independent_agreement_estimated'] is False,
            'ten_repetitions':protocol['design']['repetitions']==10,
            'base_design_count':protocol['design']['base_executions']==25*4*10,
            'campaign_not_started':protocol['final_campaign_started'] is False,
            'not_all_tests_claimed':protocol['design']['includes_all_V01_V10'] is False,
            'security_stage_not_started':protocol['security_stage']=='S04_not_authorized',
            'absolute_zero_violation_constraint':protocol['thresholds']['unauthorized_transmissions']['maximum']==0,
            'freeze_blockers_explicit':bool(protocol['freeze_blockers'])}
    approval=protocol.get('threshold_approval',{})
    digest=hashlib.sha256(json.dumps(protocol['thresholds'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    checks['thresholds_approved_without_freezing_campaign']=approval.get('status')=='approved' and approval.get('approved_by')=='user' and approval.get('scope')=='thresholds_rubric_and_descriptive_latency_policy_only' and approval.get('thresholds_sha256')==digest and 'user_threshold_approval' not in protocol['freeze_blockers']
    checks.update(annotation_checks(annotations,root/'dataset/Documents'))
    checks.update(review_checks(protocol.get('annotation_review',{}),annotations))
    evidence=json.loads((root/'evaluation/evidence_map.json').read_text())
    checks['V01_V10_mapped']=set(evidence['cases'])=={f'V-{i:02}' for i in range(1,11)}
    for key,item in evidence['cases'].items():
        checks[key+'/not_claimed_complete']=item['final_campaign_complete'] is False
        for reference in item['references']:
            path,_,symbol=reference.partition('::')
            target=root/path
            exists=target.is_file()
            if exists and symbol:
                exists=any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==symbol for n in ast.walk(ast.parse(target.read_text())))
            checks[key+'/'+reference]=exists
    with (root/'evaluation/human_review_template.csv').open(newline='') as f:
        reader=csv.DictReader(f);checks['human_template_empty']=list(reader)==[]
        checks['human_template_fields']=reader.fieldnames==['evaluation_id','case_id','report_sha256','correctness','coverage','provenance','limits','critical_error','notes']
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--require-frozen',action='store_true');a=p.parse_args()
    protocol=json.loads((ROOT/'evaluation/protocol.json').read_text());annotations=json.loads((ROOT/'evaluation/annotations.json').read_text())
    try:checks=verify(protocol,annotations)
    except (ValueError,KeyError,TypeError,OSError) as e:raise SystemExit('Bozza non valida: '+str(e))
    bad=[k for k,v in checks.items() if not v]
    print('Controlli:',len(checks));print('Problemi:',len(bad))
    for k in bad:print(k)
    print('Stato protocollo:',protocol['status'])
    print('Annotazioni confermate dal valutatore:',str(len(protocol.get('annotation_review',{}).get('confirmed_cases',{})))+'/25')
    print('Campagna finale autorizzata: False')
    if a.require_frozen:raise SystemExit('Protocollo non congelato: occorrono revisione e approvazione esplicite. Nessuna campagna avviata.')
    raise SystemExit(1 if bad else 0)

if __name__=='__main__':main()
