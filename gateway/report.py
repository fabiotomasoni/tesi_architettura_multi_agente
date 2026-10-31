"""Report locale deterministico: separa evidenze e sintesi senza inferenza aggiuntiva."""
from .policy import REQUIRED, OPTIONAL, POLICY_VERSION, make_view, issues
from .models import Scenario
from .agent_contracts import TaxView, MarketView, is_ecb_evidence
from .tax_evidence import faithful_summary
from .market_evidence import faithful_summary as market_summary
import hashlib
from .mortgage import compare_mortgage
from .tax_application import apply_tax_scenario
from .comparisons import evaluate, report_observations


def build_report(profile, scenarios, activities, status, *, comparison_observations=None):
    document_data=[]
    sources=[]
    summaries=[]
    outcomes=[]
    faithful=[]
    evaluation=[]
    completeness=[]
    limits=[
        'Le fonti simulate non attestano quotazioni o norme reali; ogni fonte è classificata separatamente.',
        'Le sintesi dei modelli non costituiscono evidenze o conclusioni verificate.',
        'I tassi statistici non sono offerte personali; eventuali calcoli sono orientativi e nessuna spettanza fiscale è calcolata.',
        'Estrazione limitata al template sintetico; validazione non significa autenticità del documento.',
        'Le citazioni riguardano il testo estratto dal parser, non coordinate grafiche o autenticità del PDF.',
    ]
    for scenario in scenarios:
        facts={}
        required=REQUIRED[Scenario(scenario)]
        optional=OPTIONAL[Scenario(scenario)]
        problems=issues(profile,Scenario(scenario))
        for name in required+optional:
            fact=getattr(profile,name)
            facts[name]=fact.model_dump(mode='json') if fact else {'status':'not_specified' if name in optional else 'missing'}
            if fact:
                facts[name]['validation_issues']=[p['reason'] for p in problems if p['field'] in {name,'period'}]
                facts[name]['provenance_status']='text_span_available' if fact.source.quote is not None and fact.source.start is not None and fact.source.end is not None and fact.source.document_sha256 else 'caller_declared_not_document_verified'
        missing=[n for n in required if getattr(profile,n) is None]
        ambiguous=[n for n in required if getattr(profile,n) is not None and getattr(profile,n).status!='validated']
        unsupported=[n for n in required if n not in missing and facts[n]['provenance_status']!='text_span_available']
        completeness.append({'scenario':scenario,'required_fields':list(required),'optional_fields':list(optional),
            'included_fields':list(facts),'missing_required':missing,'ambiguous_or_unvalidated':ambiguous,
            'without_document_span':unsupported,'validation_issues':problems,
            'optional_not_specified':[n for n in optional if getattr(profile,n) is None],
            'scope':'Copertura dei campi degli scenari richiesti, non completezza di tutte le informazioni nei PDF.'})
        if any(getattr(profile,n) is None for n in optional):
            limits.append(f'{scenario}: tipologia del mutuo non specificata; ricerca di contesto generica. Nessuna categoria inventata.')
        document_data.append({'scenario':scenario,'facts':facts})
        activity=activities[scenario]
        result=activity.get('result')
        outcomes.append({'scenario':scenario,'status':activity['status'],'error_code':activity.get('error_code'),
            'interpretation': 'Attività tecnica completata; nessuna conclusione personalizzata.' if activity['status']=='completed' else 'Provenienza obbligatoria mancante: risultato non verificato, escluso da fonti e calcoli.' if activity['status']=='unverified' else 'Risposta personalizzata non disponibile per questa attività.'})
        if result and activity['status']=='completed':
            sources.append({'scenario':scenario,'evidence':result['evidence'],'verification':'schema_and_provenance_checked','real_world_verified':False})
            if scenario=='S-02':
                # Il contesto atteso viene dal profilo locale, non dalla risposta dell'agente.
                view=TaxView(tax_year=int(str(profile.tax_year.value)),purpose=profile.purpose.value)
                checked=faithful_summary(result['evidence'],view)
                faithful.append(checked)
                limits.append(checked['limit'])
                sources[-1]['verification']='authorized_fixture_content_checked'
                sources[-1]['source_sha256']=checked['source_sha256']
                evaluation.append({'scenario':scenario,'model':result['model'],
                    'free_text_included':False,'reason':'Prosa del modello non verificata; esclusa dalla sintesi fiscale.',
                    'output_sha256':hashlib.sha256(result['summary'].encode()).hexdigest()})
            else:
                view=MarketView.model_validate(make_view(profile,Scenario.MORTGAGE))
                real=is_ecb_evidence(result['evidence'])
                if real and result.get('measurements',{}).get('gateway_source_receipt_verified')!=1:
                    raise ValueError('Ricevuta di recupero BCE del gateway assente')
                checked=market_summary(result['evidence'],view)
                faithful.append(checked)
                limits.append(checked['limit'])
                sources[-1]['verification']='gateway_retrieval_and_series_checked' if real else 'authorized_fixture_content_checked'
                if real:
                    sources[-1].pop('real_world_verified',None)
                    sources[-1]['institutional_retrieval_verified']=True
                sources[-1]['source_sha256']=checked['source_sha256']
                evaluation.append({'scenario':scenario,'model':result['model'],
                    'free_text_included':False,'reason':'Prosa del modello non verificata; esclusa dalla sintesi mercati.',
                    'output_sha256':hashlib.sha256(result['summary'].encode()).hexdigest()})
        # Le note libere dell’agente non sono fonti: i limiti del documento
        # provengono dai controlli locali e dai modelli di calcolo verificati.
        if activity['status']!='completed':
            limits.append(f"{scenario}: attività {activity['status']} ({activity.get('error_code') or 'esito incompleto'}).")
    observations=report_observations(profile,sources) if 'S-01' in scenarios else []
    if comparison_observations is not None:
        observations.extend(comparison_observations)
    consistency=evaluate(observations)
    consistency['scope']='Solo osservazioni registrate: zero conflitti non significa verifica esaustiva di tutti i documenti.'
    if consistency['unresolved_conflicts']:
        limits.append('Conflitti non risolti: conservate entrambe le provenienze; nessuna conclusione personalizzata autorizzata.')
    mortgage=compare_mortgage(profile,activities['S-01'],has_conflicts=bool(consistency['unresolved_conflicts'])) if 'S-01' in scenarios else None
    tax_application=apply_tax_scenario(profile,activities['S-02'],has_conflicts=bool(consistency['unresolved_conflicts'])) if 'S-02' in scenarios else None
    return {'tax_application':tax_application,'mortgage_comparison':mortgage,'report_version':'0.9.0','policy_version':POLICY_VERSION,'title':'Report locale di esecuzione — dati sintetici',
        'consistency':consistency,'analysis_status':'unresolved_conflict' if consistency['unresolved_conflicts'] else 'no_conflict_in_registered_observations','completeness':completeness,'status':status,'requested_scenarios':scenarios,'document_data':document_data,'simulated_sources':[s for s in sources if s['evidence'].get('simulated') is True],
        'external_sources':[s for s in sources if s['evidence'].get('simulated') is False],
        'faithful_summaries':faithful,'model_evaluation':evaluation,'unverified_summaries':summaries,'outcomes':outcomes,'limits':list(dict.fromkeys(limits))}
