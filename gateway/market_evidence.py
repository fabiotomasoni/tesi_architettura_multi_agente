"""Catalogo fidato dei tassi di test: nessuna quotazione o convenienza reale."""
from .result_validation import require_explicit_provenance
import hashlib
import json
from .agent_contracts import MarketView, RateEvidence

RATES={'fixed':'3.20','variable':'3.60','mixed':'3.40'}


def expected_evidence(view: MarketView) -> RateEvidence:
    return RateEvidence(annual_rate_percent=RATES[view.rate_type])


def verify_evidence(evidence, view: MarketView):
    require_explicit_provenance(evidence,RateEvidence,('source_id','reference_date','unit','simulated'))
    parsed=RateEvidence.model_validate(evidence)
    if parsed.model_dump()!=expected_evidence(view).model_dump():
        raise ValueError('Contenuto difforme dalla fixture mercati autorizzata')
    encoded=json.dumps(parsed.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return parsed,hashlib.sha256(encoded).hexdigest()


def faithful_summary(evidence, view: MarketView):
    parsed,digest=verify_evidence(evidence,view)
    return {'scenario':'S-01','verification':'faithful_to_authorized_fixture','method':'deterministic_extraction',
            'source_id':parsed.source_id,'source_sha256':digest,'real_world_verified':False,
            'context':view.model_dump(mode='json'),
            'statements':[
                {'text':f'Tasso annuo simulato: {parsed.annual_rate_percent}%.','source_ref':f'{parsed.source_id}#annual_rate_percent'},
                {'text':f'Data di riferimento della fixture: {parsed.reference_date}.','source_ref':f'{parsed.source_id}#reference_date'}],
            'limit':'Dato simulato, non offerta reale; nessuna conclusione di convenienza. La fixture dipende solo dal tipo di tasso.'}
