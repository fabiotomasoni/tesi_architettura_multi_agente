"""Catalogo fidato della sola fixture fiscale: non certifica norme reali."""
from .ade_source import is_ade, verify_ade, PROVENANCE_FIELDS, LIMIT
from .result_validation import require_explicit_provenance
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
    if is_ade(evidence):return verify_ade(evidence,view)
    require_explicit_provenance(evidence,TaxEvidence,('source_id','reference'))
    parsed=TaxEvidence.model_validate(evidence)
    if parsed.model_dump() != expected_evidence(view).model_dump():
        raise ValueError('Contenuto fiscale difforme dalla fixture autorizzata')
    encoded=json.dumps(parsed.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return parsed, hashlib.sha256(encoded).hexdigest()


def faithful_summary(evidence, view: TaxView) -> dict:
    parsed,digest=verify_evidence(evidence,view)
    if is_ade(parsed):
        return {'scenario':'S-02','verification':'faithful_to_gateway_verified_publication','method':'deterministic_extraction',
            'source_id':parsed.source_id,'source_sha256':digest,'institutional_retrieval_verified':True,'simulated':False,
            'context':{'tax_year':parsed.tax_year,'purpose':parsed.purpose},
            'statements':[{'text':q['text'],'source_ref':parsed.source_url+'#page='+str(q['page'])} for q in parsed.quotes],
            'limit':LIMIT}
    return {'scenario':'S-02','verification':'faithful_to_authorized_fixture','method':'deterministic_extraction',
            'source_id':parsed.source_id,'source_sha256':digest,'real_world_verified':False,
            'context':{'tax_year':parsed.tax_year,'purpose':parsed.purpose},
            'statements':[{'text':text,'source_ref':f'{parsed.source_id}#conditions/{i}'} for i,text in enumerate(parsed.conditions)],
            'limit':'Fedeltà alla fixture simulata; nessuna verifica normativa o conclusione di spettanza.'}


class TaxEvidenceParser:
    @classmethod
    def model_validate(cls,data):
        from .ade_source import AdeEvidence
        return (AdeEvidence if is_ade(data) else TaxEvidence).model_validate(data)


def provenance_fields(data):
    return PROVENANCE_FIELDS if is_ade(data) else ('source_id','reference')
