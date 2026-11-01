"""Applicazione aritmetica locale, senza interpretazione normativa o spettanza."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from .models import Scenario
from .policy import issues, domain_view
from .agent_contracts import TaxView
from .tax_evidence import verify_evidence
from .ade_source import is_ade, LIMIT


def apply_tax_scenario(profile, activity, *, has_conflicts=False):
    base={'model_version':'0.1.0','deduction_calculated':False,'tax_entitlement':'not_assessed',
          'personalized_recommendation':False,'assumptions':[
              'Solo per questo scenario, gli interessi documentati si assumono riferiti all’intero mutuo e non già ripartiti.',
              'La quota di intestazione viene usata come fattore aritmetico, non come prova di un diritto fiscale.'],
          'limits':[
              'Il PDF non chiarisce se gli interessi siano già attribuiti alla singola persona: evitare una doppia ripartizione.',
              'Fonte simulata: nessuna norma, aliquota, soglia o spettanza reale verificata.',
              'Il prodotto interessi × quota non è un importo detraibile né una detrazione spettante.',
              'Condizioni di accesso e significato fiscale dei documenti restano da verificare su fonti reali.']}
    def not_calculated(reason, **context):
        # Le ipotesi del modello e le note della fixture valgono solo per un calcolo eseguito.
        return {**base, 'assumptions': [],
                'limits': ['Calcolo non eseguito; nessun risultato numerico derivato o conclusione personalizzata.'],
                'status': 'not_calculated', 'reason': reason, **context}

    if has_conflicts:return not_calculated('unresolved_conflict')
    if issues(profile,Scenario.TAX):return not_calculated('input_not_ready')
    if activity['status']!='completed' or not activity.get('result',{}).get('evidence'):
        return not_calculated('tax_evidence_unavailable')
    evidence,digest=verify_evidence(activity['result']['evidence'],TaxView.model_validate(domain_view(profile,Scenario.TAX)))
    real=is_ade(evidence)
    if real:
        base['limits']=[x for x in base['limits'] if 'Fonte simulata' not in x and 'fonti reali' not in x]+[LIMIT]
    interest=Decimal(str(profile.annual_interest.value));share=Decimal(str(profile.ownership_share.value))
    with localcontext() as ctx:
        ctx.prec=50
        product=interest*share
        money=lambda value:str(value.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
        return {**base,'status':'calculated','calculation_type':'hypothetical_allocation_only',
            'documentary_context':{'tax_year':int(str(profile.tax_year.value)),'purpose':profile.purpose.value,
                'annual_interest_EUR':money(interest),'ownership_share':str(share)},
            'input_refs':{name:f'document_data/S-02/facts/{name}' for name in ['tax_year','purpose','annual_interest','ownership_share']},
            'hypothetical_allocation':{'formula':'annual_interest * ownership_share','amount_EUR':money(product),
                'rounding':'ROUND_HALF_UP to 0.01 EUR after multiplication',
                'origin':'derived_under_explicit_unverified_assumption','documented_as_personal_amount':False},
            'source':{'source_id':evidence.source_id,'source_sha256':digest,'simulated':evidence.simulated,**({'source_url':evidence.source_url,'publication_year':evidence.publication_year} if real else {'reference':evidence.reference})},
            'conditions_to_verify':([{'text':LIMIT,'origin':'local_scope_limit','source_ref':None,'personal_requirements_verified':False}] if real else [{'text':text,'source_ref':f'{evidence.source_id}#conditions/{i}','real_world_verified':False} for i,text in enumerate(evidence.conditions)])}
