"""Una sola serie pubblica BCE, richiesta fissa e risposte verificabili.

Non è TAN/TAEG, offerta commerciale o selezione in base al profilo.
Il controllo di origine effettiva è nel gateway, confrontando la ricevuta del ponte.
"""
import asyncio
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from io import StringIO
import json
from time import perf_counter
from typing import Literal

import httpx
from pydantic import Field, model_validator
from .models import Contract

SOURCE_ID = 'ecb-mir-it-house-purchase-v1'
SERIES_KEY = 'MIR.M.IT.B.A2C.A.R.A.2250.EUR.N'
API_ENDPOINT = 'https://data-api.ecb.europa.eu/service/data/MIR/M.IT.B.A2C.A.R.A.2250.EUR.N'
PARAMETERS = {'lastNObservations':'1', 'format':'csvdata'}
SOURCE_URL = str(httpx.URL(API_ENDPOINT, params=PARAMETERS))
PORTAL_URL = 'https://data.ecb.europa.eu/data/datasets/MIR/' + SERIES_KEY
DESTINATION = 'ecb://mir-it-house-purchase-v1'
BRIDGE_JOB = {'kind':'ecb_market_source', 'source_id':SOURCE_ID}
MAX_BYTES = 16384
WIRE_REQUEST = {'method':'GET', 'url':SOURCE_URL, 'headers':{'accept':'text/csv', 'accept-encoding':'identity'}}
REAL_MARKET_PROMPT = ('Descrivi in italiano il dato statistico BCE e il suo periodo. È un AAR/NDER aggregato sui nuovi mutui italiani, '
                      'non un TAN contrattuale, un’offerta o una previsione. Non dichiarare convenienza, risparmi o personalizzazione.')
DIMENSIONS = {'KEY':SERIES_KEY, 'FREQ':'M', 'REF_AREA':'IT', 'BS_REP_SECTOR':'B', 'BS_ITEM':'A2C',
              'MATURITY_NOT_IRATE':'A', 'DATA_TYPE_MIR':'R', 'AMOUNT_CAT':'A', 'BS_COUNT_SECTOR':'2250',
              'CURRENCY_TRANS':'EUR', 'IR_BUS_COV':'N', 'UNIT':'PCPA', 'UNIT_MULT':'0',
              'OBS_STATUS':'A', 'OBS_CONF':'F'}


def parse_csv(content):
    if len(content.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Risposta BCE troppo grande')
    rows = list(csv.reader(StringIO(content.lstrip('\ufeff'))))
    if len(rows) != 2 or len(set(rows[0])) != len(rows[0]) or len(rows[0]) != len(rows[1]):
        raise ValueError('Attesa una sola osservazione BCE con intestazioni univoche')
    row = dict(zip(rows[0], rows[1]))
    if any(row.get(k) != value for k,value in DIMENSIONS.items()):
        raise ValueError('Serie, unità o stato BCE non autorizzati')
    return row


class PublicObservation(Contract):
    source_id: Literal['ecb-mir-it-house-purchase-v1'] = SOURCE_ID
    simulated: Literal[False] = False
    series_key: Literal['MIR.M.IT.B.A2C.A.R.A.2250.EUR.N'] = SERIES_KEY
    annual_rate_percent: str = Field(pattern=r'^\d{1,2}(?:\.\d{1,10})?$')
    observation_period: str = Field(pattern=r'^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])$')
    unit: Literal['percent_per_year'] = 'percent_per_year'
    measure: Literal['AAR_NDER_aggregate_new_business'] = 'AAR_NDER_aggregate_new_business'
    scope: Literal['Italy_house_purchase_households_total_initial_fixation'] = 'Italy_house_purchase_households_total_initial_fixation'
    observation_status: Literal['A'] = 'A'

    @model_validator(mode='after')
    def valid_value(self):
        if not 0 <= Decimal(self.annual_rate_percent) <= 100:
            raise ValueError('Valore BCE non supportato')
        return self


class EcbRateEvidence(PublicObservation):
    source_url: Literal[SOURCE_URL] = SOURCE_URL
    portal_url: Literal[PORTAL_URL] = PORTAL_URL
    retrieved_at: datetime | None = None
    response_sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    source_csv: str | None = Field(default=None, max_length=MAX_BYTES)

    @model_validator(mode='after')
    def consistent_observation(self):
        if self.retrieved_at is not None:
            if self.retrieved_at.tzinfo is None or self.observation_period > self.retrieved_at.strftime('%Y-%m'):
                raise ValueError('Periodo BCE futuro o recupero senza fuso orario')
        if self.source_csv is not None:
            row = parse_csv(self.source_csv)
            if row.get('OBS_VALUE') != self.annual_rate_percent or row.get('TIME_PERIOD') != self.observation_period:
                raise ValueError('Valore o periodo difforme dalla citazione BCE')
            if self.response_sha256 is not None and hashlib.sha256(self.source_csv.encode('utf-8')).hexdigest() != self.response_sha256:
                raise ValueError('Digest della risposta BCE difforme')
        return self


PROVENANCE_FIELDS = ('source_id','simulated','series_key','unit','measure','scope','observation_status',
                     'source_url','portal_url','retrieved_at','response_sha256','source_csv')


def verify_ecb(evidence):
    from .result_validation import require_explicit_provenance
    require_explicit_provenance(evidence,EcbRateEvidence,PROVENANCE_FIELDS)
    parsed = EcbRateEvidence.model_validate(evidence)
    if any(getattr(parsed,k) is None for k in PROVENANCE_FIELDS):
        raise ValueError('Provenienza BCE incompleta')
    encoded = json.dumps(parsed.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return parsed, hashlib.sha256(encoded).hexdigest()


def public_prompt_data(evidence):
    data = evidence.model_dump(mode='json') if hasattr(evidence,'model_dump') else evidence
    return PublicObservation.model_validate({k:data[k] for k in PublicObservation.model_fields}).model_dump(mode='json')


async def fetch_ecb():
    """Nessun argomento del chiamante e nessun redirect/retry/cookie/credenziale."""
    started = perf_counter()
    async with asyncio.timeout(20):
        async with httpx.AsyncClient(timeout=20,trust_env=False,follow_redirects=False) as client:
            async with client.stream('GET',SOURCE_URL,headers=WIRE_REQUEST['headers']) as response:
                if response.status_code != 200 or str(response.url) != SOURCE_URL:
                    raise ValueError('Risposta o destinazione BCE non autorizzata')
                if 'text/csv' not in response.headers.get('content-type','').lower():
                    raise ValueError('Formato BCE non CSV')
                if response.headers.get('content-encoding','identity').lower() not in ('','identity'):
                    raise ValueError('Codifica BCE non supportata')
                raw = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=1024):
                    raw.extend(chunk)
                    if len(raw) > MAX_BYTES:
                        raise ValueError('Risposta BCE troppo grande')
    content = raw.decode('utf-8')
    row = parse_csv(content)
    evidence = EcbRateEvidence(annual_rate_percent=row['OBS_VALUE'],observation_period=row['TIME_PERIOD'],
        retrieved_at=datetime.now(timezone.utc),source_csv=content,response_sha256=hashlib.sha256(raw).hexdigest())
    evidence,_ = verify_ecb(evidence)
    return evidence, round((perf_counter()-started)*1000,3)
