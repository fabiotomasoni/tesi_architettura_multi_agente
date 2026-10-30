"""Catalogo fidato della sola fixture fiscale: non certifica norme reali."""
import hashlib
import json
from .agent_contracts import TaxEvidence, TaxView

CONDITIONS = (
    'DEMO: verificare requisiti documentali per la finalità dichiarata.',
    'DEMO: verificare condizioni personali non certificate dai PDF.',
    'Nessuna aliquota, soglia o spettanza reale viene attestata.',
)


def expected_evidence(view: TaxView) -> TaxEvidence:
    return TaxEvidence(tax_year=view.tax_year, purpose=view.purpose, conditions=list(CONDITIONS))


def verify_evidence(evidence, view: TaxView) -> tuple[TaxEvidence, str]:
    parsed=TaxEvidence.model_validate(evidence)
    if parsed.model_dump() != expected_evidence(view).model_dump():
        raise ValueError('Contenuto fiscale difforme dalla fixture autorizzata')
    encoded=json.dumps(parsed.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return parsed, hashlib.sha256(encoded).hexdigest()


def faithful_summary(evidence, view: TaxView) -> dict:
    parsed,digest=verify_evidence(evidence,view)
    return {'scenario':'S-02','verification':'faithful_to_authorized_fixture','method':'deterministic_extraction',
            'source_id':parsed.source_id,'source_sha256':digest,'real_world_verified':False,
            'context':{'tax_year':parsed.tax_year,'purpose':parsed.purpose},
            'statements':[{'text':text,'source_ref':f'{parsed.source_id}#conditions/{i}'} for i,text in enumerate(parsed.conditions)],
            'limit':'Fedeltà alla fixture simulata; nessuna verifica normativa o conclusione di spettanza.'}
