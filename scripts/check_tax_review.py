"""Controllo locale del riepilogo e citazioni annuali; non verifica la spettanza o esegue nuove richieste."""
import argparse,json
from pathlib import Path
from gateway.tax_review_rules import RULES, EDITION_DIGESTS
from gateway.tax_review import RULE_GROUPS
from gateway.ade_source import verify_ade
from gateway.agent_contracts import TaxView


def verify(report):
    review=report.get('tax_review')
    checks={'tax_review_present':review is not None}
    if review is None:return checks
    try:
        facts=next(x['facts'] for x in report['document_data'] if x['scenario']=='S-02')
        expected={n:{k:v for k,v in facts[n].items() if k not in {'validation_issues','provenance_status'}} for n in ('tax_year','purpose','annual_interest','ownership_share')}
        checks.update(documentary_context_preserved=review['documentary_context']==expected,
            no_deduction=review['deduction_calculated'] is False,
            no_entitlement=review['tax_entitlement']=='not_assessed',
            no_recommendation=review['personalized_recommendation'] is False,
            limits_explicit=bool(review['limits']) and bool(review['conclusion']))
        if review['status']=='not_assessed':
            reason=review.get('reason');activity=next(a for a in report['outcomes'] if a['scenario']=='S-02')
            sources=[s for s in report.get('simulated_sources',[])+report.get('external_sources',[]) if s['scenario']=='S-02']
            problems=next(x for x in report['completeness'] if x['scenario']=='S-02')
            checks['unavailable_reason_valid']=(reason=='input_not_ready' and bool(problems['validation_issues']) or
                reason=='tax_evidence_unavailable' and activity['status']!='completed' or
                reason=='simulated_source_only' and any(s['evidence']['simulated'] is True for s in sources) or
                reason=='unresolved_conflict' and report['consistency']['unresolved_conflicts']>0)
            checks['no_invented_conditions_or_source']=review['conditions']==[] and 'source' not in review
            return checks
        checks['conditions_status']=review['status']=='conditions_identified'
        source=next(s for s in report['external_sources'] if s['scenario']=='S-02')
        e,digest=verify_ade(source['evidence'],TaxView(tax_year=int(facts['tax_year']['value']),purpose=facts['purpose']['value']))
        checks['rules_edition_matches']=EDITION_DIGESTS.get(str(e.tax_year))==e.document_sha256
        checks['verified_receipt']=source['verification']=='gateway_retrieval_and_publication_checked' and source['institutional_retrieval_verified'] is True
        checks['review_source_matches']=source['source_sha256']==digest and review['source']=={'source_id':e.source_id,'source_sha256':digest,'document_sha256':e.document_sha256,'tax_year':e.tax_year,'publication_year':e.publication_year,'source_url':e.source_url,'retrieved_at':e.retrieved_at.isoformat()}
        expected_ids=list(RULE_GROUPS[e.purpose]);conditions=review['conditions']
        checks['relevant_conditions_complete']=[x['condition_id'] for x in conditions]==expected_ids
        checks['conditions_not_personally_verified']=all(x['status']=='to_verify' and x['personal_verification']=='not_assessed_from_supported_fields' and x['applicability']=='candidate_only' for x in conditions)
        checks['faithful_rule_citations']=all(x['source']=={'source_id':e.source_id,'source_url':e.source_url,'source_ref':e.source_url+'#page='+str(RULES[str(e.tax_year)][x['condition_id']]['page']),'page':RULES[str(e.tax_year)][x['condition_id']]['page'],'quote':RULES[str(e.tax_year)][x['condition_id']]['quote'],'tax_year':e.tax_year,'publication_year':e.publication_year,'document_sha256':e.document_sha256} and all(x[k]==RULES[str(e.tax_year)][x['condition_id']][k] for k in ('title','question','needed_information')) for x in conditions)
    except (KeyError,ValueError,TypeError,StopIteration):checks['complete_valid_review']=False
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path);args=p.parse_args()
    checks=verify(json.loads(args.report.read_text()))
    for k,v in checks.items():print(k+': '+str(bool(v)))
    raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
