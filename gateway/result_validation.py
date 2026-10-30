"""La provenienza ricevuta deve essere esplicita: i default non la inventano."""
import json
from uuid import UUID


def parse_result(text, task, result_type, evidence_type, provenance_fields):
    raw=json.loads(text)
    if not isinstance(raw,dict):raise ValueError('Risultato non strutturato')
    if UUID(str(raw.get('correlation_id'))) != task.correlation_id:
        raise ValueError('Correlazione non valida')
    missing=[]
    evidence=raw.get('evidence')
    if raw.get('status')=='completed':
        if raw.get('error_code') is not None:raise ValueError('Completamento con errore incoerente')
        if evidence is None:missing=['evidence']
        elif isinstance(evidence,dict):
            missing=[name for name in provenance_fields if evidence.get(name) in (None,'')]
            # Verificare il contenuto nonostante eventuali metadati omessi.
            candidate={k:v for k,v in evidence.items() if not (k in missing and v in (None,''))}
            evidence_type.model_validate(candidate)
        else:raise ValueError('Evidenza malformata')
    if not missing:return result_type.model_validate(raw)
    # Validare l'envelope originale prima di rimuovere contenuti non utilizzabili.
    envelope={**raw,'status':'failed','error_code':None,'evidence':None}
    validated=result_type.model_validate(envelope)
    return result_type(correlation_id=validated.correlation_id,status='unverified',error_code='missing_provenance',
        evidence=None,summary='Risultato senza provenienza obbligatoria; contenuto escluso.',model=validated.model,
        limits=['Provenienza obbligatoria mancante: '+', '.join(missing)+'. Nessun dato di questo risultato è usato per conclusioni o calcoli.'],
        measurements={'provenance_verified':0})


class MissingProvenanceError(ValueError):
    """Contenuto strutturato senza i metadati di provenienza obbligatori."""


def require_explicit_provenance(evidence, evidence_type, fields):
    if not isinstance(evidence,dict):
        return
    missing=[field for field in fields if evidence.get(field) in (None,'')]
    # Non confondere un contenuto malformato con la sola omissione della fonte.
    candidate={k:v for k,v in evidence.items() if not (k in missing and v in (None,''))}
    evidence_type.model_validate(candidate)
    if missing:
        raise MissingProvenanceError('Provenienza obbligatoria mancante: '+', '.join(missing))
