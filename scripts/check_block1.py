"""Pilota della demo con fonti reali; controlli tecnici, non valutazione umana."""
import argparse
import json
from pathlib import Path

import httpx
from gateway.agent_contracts import MarketView, TaxView
from gateway.models import Profile, Fact, Scenario
from gateway.policy import domain_view
from gateway.market_analysis import report_analysis as market_analysis
from gateway.tax_analysis import report_analysis as tax_analysis
from gateway.report_document import render_report_document
if __package__:
    from .check_report_provenance import verify as provenance
    from .check_mortgage import verify as mortgage
    from .check_tax_application import verify as tax_application
    from .check_tax_review import verify as tax_review
    from .check_ecb_report import verify as ecb
    from .check_ade_report import verify as ade
    from .trace_export import record_trace
else:
    from check_report_provenance import verify as provenance
    from check_mortgage import verify as mortgage
    from check_tax_application import verify as tax_application
    from check_tax_review import verify as tax_review
    from check_ecb_report import verify as ecb
    from check_ade_report import verify as ade
    from trace_export import record_trace


ROOT=Path(__file__).resolve().parents[1]
CASES=('C001','C024','C006','C011','C021')


def expected_activities(case):
    n=int(case[1:])
    return {'S-01':'blocked' if 6<=n<=10 or 16<=n<=20 else 'completed',
            'S-02':'blocked' if 11<=n<=15 else 'completed'}


def verify_report(report, expected):
    """Ricontrolla il JSON, il catalogo delle selezioni e i PDF locali originali."""
    checked,problems=provenance(report,ROOT/'dataset'/'Documents')
    checks={'documentary_provenance':checked>0 and not problems,
            'requested_scenarios':set(report['requested_scenarios'])==set(expected),
            'no_simulated_fallback':not report.get('simulated_sources'),
            'report_version':report.get('report_version')=='0.16.0',
            'source_inventory':sorted(x['scenario'] for x in report.get('external_sources',[]))==sorted(s for s,v in expected.items() if v=='completed')}
    for prefix,verify in [('mortgage',mortgage),('tax_application',tax_application),('tax_review',tax_review)]:
        checks.update({prefix+'/'+key:value for key,value in verify(report).items()})
    facts={key:value for section in report['document_data'] for key,value in section['facts'].items()
           if value.get('status') not in {'missing','not_specified'}}
    p=Profile.model_validate({key:{k:v for k,v in fact.items() if k in Fact.model_fields}
                              for key,fact in facts.items()})
    analyses=report.get('model_analyses',[])
    checks['model_inventory']=sorted(a['scenario'] for a in analyses)==sorted(s for s,v in expected.items() if v=='completed')
    for scenario,state in expected.items():
        if state!='completed':continue
        source_checks=ecb(report) if scenario=='S-01' else ade(report)
        checks.update({scenario+'/'+key:value for key,value in source_checks.items()})
        entries=[a for a in analyses if a.get('scenario')==scenario]
        if len(entries)!=1:continue
        item=entries[0]
        checks[scenario+'/selection_available']=item.get('status') in {'available','selection_only'}
        checks[scenario+'/not_semantically_certified']=item.get('semantic_verified') is False and item.get('selection_relevance_verified') is False
        checks[scenario+'/gateway_model_receipt']=item.get('gateway_model_output_receipt_verified') is True
        source=next(s['evidence'] for s in report['external_sources'] if s['scenario']==scenario)
        view=domain_view(p,Scenario(scenario))
        fiscal=scenario=='S-02'
        regenerated=(tax_analysis if fiscal else market_analysis)(
            {'tax_analysis' if fiscal else 'market_analysis':item,'model':item.get('model'),
             'measurements':{'gateway_analysis_receipt_verified':1 if item.get('gateway_model_output_receipt_verified') is True else 0}},
            (TaxView if fiscal else MarketView).model_validate(view),source)
        checks[scenario+'/catalog_and_references']=all(regenerated.get(k)==item.get(k)
            for k in ('status','selected_statements','references','source_sha256','content'))
        if fiscal:
            checks[scenario+'/no_personal_entitlement']=item.get('tax_entitlement')=='not_assessed' and item.get('deduction_calculated') is False and item.get('personalized_recommendation') is False
        if item.get('status')=='selection_only':
            checks[scenario+'/excluded_comment_absent']=(item.get('content') or {}).get('explanation') is None
    return checks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('runs/block1_manual.json'))
    parser.add_argument('--reports-dir',type=Path,help='Esportazione esplicita dei report sintetici JSON e HTML sul client.')
    args=parser.parse_args()
    if args.output.exists():parser.error('Il file di esito esiste già: scegliere un altro nome.')
    if args.reports_dir and args.reports_dir.exists():parser.error('La cartella dei report esiste già: scegliere un altro nome.')
    rows=[]
    try:
        with httpx.Client(base_url='http://127.0.0.1:8080',timeout=150,trust_env=False) as client:
            response=client.get('/health');response.raise_for_status();health=response.json()
            required={'runtime_mode':'isolated','experiment':'off','minimization':'active',
                      'market_source':'ecb','tax_source':'ade','market_analysis_version':'market-selection-1',
                      'tax_analysis_version':'tax-selection-1','runtime_protocol':'financial-profile-2x2-v6'}
            if any(health.get(k)!=v for k,v in required.items()):
                parser.error('Servono la demo aggiornata e le fonti BCE/AdE attive. Ricostruire immagine e riavviare i tre servizi e il ponte.')
            for case in CASES:
                sid=None;trace_id=None
                row={'case':case,'status':'error','passed':False,'cleanup_verified':False}
                try:
                    files=[('files',(kind+'.pdf',(ROOT/'dataset'/'Documents'/f'{case}_{kind}.pdf').read_bytes(),'application/pdf')) for kind in ('mutuo','interessi')]
                    created=client.post('/sessions/pdf',files=files,data={'scenarios':['S-01','S-02']});created.raise_for_status()
                    sid=created.json()['session_id'];trace_id=created.json().get('trace_id')
                    reply=client.post(f'/sessions/{sid}/analysis');reply.raise_for_status();body=reply.json()
                    report=body['report'];expected=expected_activities(case)
                    checks=verify_report(report,expected)
                    checks['activity_outcomes']={s:a['status'] for s,a in body['activities'].items()}==expected
                    checks['automatic_session_closed']=body.get('session_closed') is True
                    checks['same_gateway_boot']=client.get('/health').json()['gateway_boot_id']==health['gateway_boot_id']
                    row.update(status=body['status'],checks=checks,passed=all(checks.values()),
                               model_statuses={a['scenario']:a['status'] for a in report.get('model_analyses',[])},
                               human_quality='not_automatically_assessed')
                    if args.reports_dir:
                        args.reports_dir.mkdir(parents=True,exist_ok=True)
                        (args.reports_dir/(case+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                        (args.reports_dir/(case+'.html')).write_text('<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Report locale</title><style>'+(ROOT/'gateway/static/app.css').read_text(encoding='utf-8')+'</style></head><body><main>'+render_report_document(report)+'</main></body></html>',encoding='utf-8')
                except (httpx.HTTPError,KeyError,ValueError,TypeError,StopIteration,OSError):
                    row['passed']=False
                    row['error']='Controllo non completato; nessun successo registrato.'
                finally:
                    record_trace(client,row,trace_id)
                    if sid:
                        try:
                            row['cleanup_verified']=client.delete(f'/sessions/{sid}').status_code==404 and all(
                                client.post(f'/sessions/{sid}/views',json={'scenario':s,'recipient':r}).status_code==404
                                for s,r in [('S-01','markets'),('S-02','tax')])
                        except httpx.HTTPError:pass
                    row['passed']=row['passed'] and row.get('trace_verified',False) and row['cleanup_verified']
                    rows.append(row)
                    print(case,row['status'],'passed:',row['passed'],'pulizia:',row['cleanup_verified'],flush=True)
    except httpx.HTTPError:
        parser.error('Gateway non raggiungibile; avviare la demo aggiornata.')
    payload={'scope':'real_source_demo_pilot_not_final_campaign_or_semantic_certification',
             'runtime_protocol':'financial-profile-2x2-v6','cases':rows,'passed':all(r['passed'] for r in rows)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    print('passed:',payload['passed'])
    raise SystemExit(0 if payload['passed'] else 1)


if __name__=='__main__':main()
