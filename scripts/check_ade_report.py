"""Coerenza locale del report con il catalogo AdE; non esegue un nuovo recupero Internet."""
import argparse,json
from pathlib import Path
from gateway.ade_source import verify_ade
from gateway.agent_contracts import TaxView


def verify(report):
    sources=[s for s in report.get('external_sources',[]) if s.get('scenario')=='S-02']
    checks={'official_tax_source_present':len(sources)==1}
    if len(sources)!=1:return checks
    try:
        facts=next(d['facts'] for d in report['document_data'] if d['scenario']=='S-02')
        view=TaxView(tax_year=int(facts['tax_year']['value']),purpose=facts['purpose']['value'])
        source=sources[0];e,digest=verify_ade(source['evidence'],view)
        checks.update(publication_year_correct=e.publication_year==view.tax_year+1,
            catalog_quotes_and_document_checked=True,
            evidence_digest_matches=source['source_sha256']==digest,
            gateway_receipt_checked=source.get('verification')=='gateway_retrieval_and_publication_checked' and source.get('institutional_retrieval_verified') is True,
            no_fixture_fallback=not any(s['scenario']=='S-02' for s in report.get('simulated_sources',[])),
            no_deduction=report['tax_application']['deduction_calculated'] is False,
            no_entitlement=report['tax_application']['tax_entitlement']=='not_assessed')
        summary=next(s for s in report['faithful_summaries'] if s['scenario']=='S-02')
        checks['faithful_citations']=summary['statements']==[{'text':q['text'],'source_ref':e.source_url+'#page='+str(q['page'])} for q in e.quotes]
    except (ValueError,KeyError,TypeError,StopIteration):checks['valid_complete_contract']=False
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path);args=p.parse_args()
    checks=verify(json.loads(args.report.read_text()))
    for k,v in checks.items():print(k+': '+str(v))
    raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
