"""Approfondimenti fiscali locali da fonti controllate: mai valutazione della spettanza."""
from copy import deepcopy
from .models import Scenario
from .policy import REQUIRED, issues
from .agent_contracts import TaxView
from .ade_source import is_ade, verify_ade
from .tax_review_rules import RULES, EDITION_DIGESTS

FIELDS=REQUIRED[Scenario.TAX]
RULE_GROUPS={
    'primary_home_purchase':('paid_year','own_share','purchase_purpose','purchase_borrower','purchase_dates','loan_changes'),
    'renovation':('paid_year','own_share','renovation_1997','renovation_qualification','renovation_dates','renovation_use','renovation_documents','renovation_loan_changes'),
    'primary_home_construction':('paid_year','own_share','renovation_qualification','renovation_dates','renovation_use','renovation_documents','renovation_loan_changes'),
    'other':('paid_year','own_share'),
}
SCOPES={
    'primary_home_purchase':'Possibile approfondimento degli interessi del mutuo per acquisto dell’abitazione principale; requisiti non accertati.',
    'renovation':'Finalità generica: distinguere il caso storico dei mutui del 1997 dal possibile percorso costruzione/ristrutturazione edilizia dell’abitazione principale. Nessun regime selezionato automaticamente.',
    'primary_home_construction':'Possibile approfondimento del mutuo per costruzione dell’abitazione principale; qualificazione, date e requisiti non accertati.',
    'other':'Finalità non classificata per un approfondimento specifico: nessun regime fiscale individuato.',
}
LIMITS=[
    'Elenco selettivo di approfondimenti, non verifica esaustiva della normativa o della dichiarazione.',
    'I dati presenti nel profilo documentale non provano automaticamente pagamento, quota fiscalmente utilizzabile o spettanza.',
    'Le informazioni richieste non sono valutate dai campi supportati del prototipo: potrebbero essere presenti nei PDF senza essere estratte.',
    'Nessuna aliquota applicata, codice dichiarativo assegnato o detrazione calcolata.',
]


def build_tax_review(profile, activity, *, has_conflicts=False):
    facts={name:(getattr(profile,name).model_dump(mode='json') if getattr(profile,name) is not None else {'status':'missing'}) for name in FIELDS}
    base={'review_version':'0.1.0','deduction_calculated':False,'tax_entitlement':'not_assessed',
          'personalized_recommendation':False,'documentary_context':facts,
          'input_refs':{n:f'document_data/S-02/facts/{n}' for n in FIELDS},
          'conditions':[],'limits':list(LIMITS)}
    def unavailable(reason):
        return {**base,'status':'not_assessed','reason':reason,
                'conclusion':'Approfondimento fiscale non disponibile per questo esito; nessuna condizione personale dichiarata soddisfatta.'}
    if has_conflicts:return unavailable('unresolved_conflict')
    problems=issues(profile,Scenario.TAX)
    if problems:return {**unavailable('input_not_ready'),'input_issues':problems}
    result=activity.get('result') or {}
    if activity.get('status')!='completed' or not result.get('evidence'):
        return unavailable('tax_evidence_unavailable')
    if not is_ade(result['evidence']):return unavailable('simulated_source_only')
    if result.get('measurements',{}).get('gateway_source_receipt_verified')!=1:
        raise ValueError('Ricevuta pubblicazione AdE assente nel riepilogo')
    view=TaxView(tax_year=int(str(profile.tax_year.value)),purpose=profile.purpose.value)
    evidence,digest=verify_ade(result['evidence'],view)
    if EDITION_DIGESTS.get(str(view.tax_year))!=evidence.document_sha256:
        raise ValueError('Edizione fiscale diversa dal catalogo delle condizioni')
    conditions=[]
    for key in RULE_GROUPS[view.purpose]:
        rule=deepcopy(RULES[str(view.tax_year)][key])
        page=rule.pop('page');quote=rule.pop('quote')
        conditions.append({'condition_id':key,**rule,'status':'to_verify',
            'personal_verification':'not_assessed_from_supported_fields','applicability':'candidate_only',
            'source':{'source_id':evidence.source_id,'source_url':evidence.source_url,
                'source_ref':evidence.source_url+'#page='+str(page),'page':page,'quote':quote,
                'tax_year':view.tax_year,'publication_year':evidence.publication_year,
                'document_sha256':evidence.document_sha256}})
    return {**base,'status':'conditions_identified','candidate_scope':SCOPES[view.purpose],
        'source':{'source_id':evidence.source_id,'source_sha256':digest,'document_sha256':evidence.document_sha256,
                  'tax_year':view.tax_year,'publication_year':evidence.publication_year,'source_url':evidence.source_url,
                  'retrieved_at':evidence.retrieved_at.isoformat()},
        'conditions':conditions,
        'conclusion':'Sono individuati riferimenti e verifiche da approfondire, non requisiti soddisfatti. La ripartizione interessi × quota resta un’ipotesi aritmetica separata, non una detrazione.'}
