"""Due pubblicazioni AdE fissate: HTTPS pubblico, nessuna ricerca o URL dal chiamante."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from time import perf_counter
from typing import Literal
import httpx
from pydantic import Field, model_validator
from .models import Contract
from .tax_publications import PUBLICATIONS

DESTINATION='ade://annual-mortgage-instructions-v1'
REAL_TAX_PROMPT='Descrivi in italiano gli estratti delle istruzioni fiscali ufficiali e il loro anno. Non attribuire codici, detrazioni o spettanza personale. Segnala che requisiti documentali e personali restano da verificare. /no_think'
LIMIT='Pubblicazione ufficiale pertinente all’anno, non verifica della spettanza. Data di stipula, eventuali modifiche del mutuo, requisiti personali e immobiliari non accertati. La finalità generica ristrutturazione non prova la categoria fiscale applicabile.'
MAX_BYTES=5*1024*1024
PROVENANCE_FIELDS=('source_id','simulated','tax_year','publication_year','source_url','document_sha256','retrieved_at','quotes','purpose')


def publication(year):
    if str(year) not in PUBLICATIONS:raise ValueError('Anno fiscale non supportato dal catalogo AdE')
    return PUBLICATIONS[str(year)]


def source_job(year):
    publication(year)
    return {'kind':'ade_tax_source','tax_year':year}


class AdeEvidence(Contract):
    source_id: Literal['ade-annual-mortgage-v1']='ade-annual-mortgage-v1'
    simulated: Literal[False]=False
    tax_year: int
    publication_year: int
    purpose: Literal['primary_home_purchase','primary_home_construction','renovation','other']
    source_url: str
    document_sha256: str
    retrieved_at: datetime
    quotes: list[dict]

    @model_validator(mode='after')
    def match_catalog(self):
        p=publication(self.tax_year)
        if any(getattr(self,k)!=p[k] for k in ('publication_year','source_url','document_sha256')) or self.quotes!=selected_quotes(self.tax_year,self.purpose):
            raise ValueError('Pubblicazione o citazioni AdE difformi dal catalogo verificato')
        if self.retrieved_at.tzinfo is None or self.retrieved_at.year<self.publication_year:
            raise ValueError('Momento di recupero AdE non valido')
        return self


def is_ade(data):
    return isinstance(data,AdeEvidence) or isinstance(data,dict) and (data.get('source_id')=='ade-annual-mortgage-v1' or data.get('simulated') is False)


def verify_ade(data, view):
    from .result_validation import require_explicit_provenance
    require_explicit_provenance(data,AdeEvidence,PROVENANCE_FIELDS)
    p=AdeEvidence.model_validate(data)
    if p.tax_year!=view.tax_year or p.purpose!=view.purpose:raise ValueError('Contesto fiscale difforme')
    return p,hashlib.sha256(json.dumps(p.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def prompt_data(evidence):
    return {k:v for k,v in evidence.model_dump(mode='json').items() if k in {'source_id','simulated','tax_year','publication_year','quotes'}}


async def fetch_ade(year):
    p=publication(year);started=perf_counter()
    from . import http_observation
    from .budgets import BUDGETS
    http_observation.select('ade')
    seconds=min(25,BUDGETS.source_seconds)
    async with asyncio.timeout(seconds):
        async with httpx.AsyncClient(timeout=seconds,trust_env=False,follow_redirects=False) as client:
            http_observation.dispatch()
            async with client.stream('GET',p['source_url'],headers={'accept':'application/pdf','accept-encoding':'identity'}) as response:
                http_observation.response()
                if response.status_code!=200 or str(response.url)!=p['source_url'] or 'application/pdf' not in response.headers.get('content-type','').lower():
                    raise ValueError('Recupero AdE non conforme')
                if response.headers.get('content-encoding','identity').lower() not in ('','identity'):raise ValueError('Codifica AdE non supportata')
                raw=bytearray()
                async for chunk in response.aiter_bytes(chunk_size=16384):
                    raw.extend(chunk)
                    if len(raw)>MAX_BYTES:raise ValueError('PDF AdE troppo grande')
    if not raw.startswith(b'%PDF-') or hashlib.sha256(raw).hexdigest()!=p['document_sha256']:
        raise ValueError('Edizione AdE cambiata o risposta non autentica rispetto all’edizione verificata')
    # Solo metadati pubblici: il gateway aggiunge il contesto autorizzato del compito.
    return {**p,'retrieved_at':datetime.now(timezone.utc).isoformat()},round((perf_counter()-started)*1000,3)


def selected_quotes(year,purpose):
    q=publication(year)['quotes']
    return [q[0],q[1]] if purpose=='primary_home_purchase' else [q[0],*q[2:]] if purpose in {'renovation','primary_home_construction'} else [q[0]]
