"""Report locale deterministico: separa evidenze e sintesi senza inferenza aggiuntiva."""
from .policy import REQUIRED, POLICY_VERSION, make_view
from .models import Scenario
from .agent_contracts import TaxView, MarketView
from .tax_evidence import faithful_summary
from .market_evidence import faithful_summary as market_summary
import hashlib


def build_report(profile, scenarios, activities, status):
    document_data=[]
    sources=[]
    summaries=[]
    outcomes=[]
    faithful=[]
    evaluation=[]
    limits=[
        'Fonti esterne sostituite da fixture simulate: nessuna quotazione o norma reale verificata.',
        'Le sintesi dei modelli non costituiscono evidenze o conclusioni verificate.',
        'Nessun calcolo di convenienza del mutuo o di spettanza fiscale eseguito.',
        'Estrazione limitata al template sintetico; validazione non significa autenticità del documento.',
        'Provenienza disponibile per documento e pagina, non ancora per porzione puntuale di testo.',
    ]
    for scenario in scenarios:
        facts={}
        for name in REQUIRED[Scenario(scenario)]:
            fact=getattr(profile,name)
            facts[name]=fact.model_dump(mode='json') if fact else {'status':'missing'}
        document_data.append({'scenario':scenario,'facts':facts})
        activity=activities[scenario]
        result=activity.get('result')
        outcomes.append({'scenario':scenario,'status':activity['status'],'error_code':activity.get('error_code'),
            'interpretation': 'Attività tecnica completata; nessuna conclusione personalizzata.' if activity['status']=='completed' else 'Risposta personalizzata non disponibile per questa attività.'})
        if result and activity['status']=='completed':
            sources.append({'scenario':scenario,'evidence':result['evidence'],'verification':'schema_and_provenance_checked','real_world_verified':False})
            if scenario=='S-02':
                # Il contesto atteso viene dal profilo locale, non dalla risposta dell'agente.
                view=TaxView(tax_year=int(str(profile.tax_year.value)),purpose=profile.purpose.value)
                checked=faithful_summary(result['evidence'],view)
                faithful.append(checked)
                sources[-1]['verification']='authorized_fixture_content_checked'
                sources[-1]['source_sha256']=checked['source_sha256']
                evaluation.append({'scenario':scenario,'model':result['model'],
                    'free_text_included':False,'reason':'Prosa del modello non verificata; esclusa dalla sintesi fiscale.',
                    'output_sha256':hashlib.sha256(result['summary'].encode()).hexdigest()})
            else:
                view=MarketView.model_validate(make_view(profile,Scenario.MORTGAGE))
                checked=market_summary(result['evidence'],view)
                faithful.append(checked)
                sources[-1]['verification']='authorized_fixture_content_checked'
                sources[-1]['source_sha256']=checked['source_sha256']
                evaluation.append({'scenario':scenario,'model':result['model'],
                    'free_text_included':False,'reason':'Prosa del modello non verificata; esclusa dalla sintesi mercati.',
                    'output_sha256':hashlib.sha256(result['summary'].encode()).hexdigest()})
        if result:
            limits.extend(result.get('limits',[]))
        if activity['status']!='completed':
            limits.append(f"{scenario}: attività {activity['status']} ({activity.get('error_code') or 'esito incompleto'}).")
    return {'report_version':'0.3.0','policy_version':POLICY_VERSION,'title':'Report locale di esecuzione — dati sintetici',
        'status':status,'requested_scenarios':scenarios,'document_data':document_data,'simulated_sources':sources,
        'faithful_summaries':faithful,'model_evaluation':evaluation,'unverified_summaries':summaries,'outcomes':outcomes,'limits':list(dict.fromkeys(limits))}
