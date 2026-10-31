"""Ponte host autenticato: ritira incarichi dal gateway, usa solo Ollama loopback.

Non ascolta su alcuna porta. Due worker servono i due rami; nessun retry inferenza.
"""
import asyncio
import json
from time import perf_counter
from pathlib import Path
import httpx
from gateway.inference import MODELS, PROMPTS
from gateway.agent_contracts import MarketView, TaxView
from gateway.market_evidence import verify_evidence as market
from gateway.tax_evidence import verify_evidence as tax

BASE='http://127.0.0.1:8080'
OLLAMA='http://127.0.0.1:11434/api/chat'
ROOT=Path(__file__).resolve().parents[1]


def validate_payload(payload):
    # Controllo aggiuntivo del ponte: non è un proxy HTTP generico né una API Ollama.
    if not isinstance(payload,dict) or payload.get('model') not in MODELS.values():
        raise ValueError('Modello non autorizzato')
    scenario=next(k for k,v in MODELS.items() if v==payload['model'])
    messages=payload['messages']
    evidence=json.loads(messages[1]['content'])
    if scenario=='S-01':
        from gateway.market_evidence import RATES
        rate=next((k for k,v in RATES.items() if v==evidence.get('annual_rate_percent')),None)
        view=MarketView(mortgage_type='not_specified',rate_type=rate,remaining_years_band={'lower_exclusive':0,'upper_inclusive':5})
        market(evidence,view)
    else:
        view=TaxView(tax_year=evidence.get('tax_year'),purpose=evidence.get('purpose'))
        tax(evidence,view)
    expected={'model':MODELS[scenario],'stream':False,'keep_alive':0,
              'options':{'num_ctx':4096,'num_predict':200,'temperature':0},
              'messages':[{'role':'system','content':PROMPTS[scenario]},
                          {'role':'user','content':messages[1]['content']}]}
    if scenario=='S-02':expected['think']=False
    if payload!=expected:
        raise ValueError('Payload non autorizzato')
    return payload


async def worker(key):
    async with httpx.AsyncClient(trust_env=False,follow_redirects=False,timeout=25,headers={'x-tesi-service-key':key}) as gateway:
        async with httpx.AsyncClient(trust_env=False,follow_redirects=False,timeout=90) as model:
            while True:
                try:
                    response=await gateway.get(BASE+'/_bridge/poll')
                    if response.status_code==204:continue
                    response.raise_for_status()
                    job=response.json()
                except httpx.HTTPError:
                    print('Gateway non disponibile o ponte non autorizzato; nuovo controllo tra 3 secondi.',flush=True)
                    await asyncio.sleep(3)
                    continue
                body=None;error=None;ollama_ms=None
                try:
                    payload=validate_payload(job['payload'])
                    started=perf_counter()
                    response=await model.post(OLLAMA,json=payload)
                    response.raise_for_status()
                    # Non esportare corpi completi senza limite al gateway.
                    if len(response.content)>60000:raise ValueError('Risposta troppo grande')
                    body=response.json()
                    ollama_ms=round((perf_counter()-started)*1000,3)
                except (TimeoutError,httpx.TimeoutException):error='timeout'
                except Exception:error='unavailable'
                try:
                    response=await gateway.post(BASE+'/_bridge/result/'+job['job_id'],json={'body':body,'error':error,'ollama_ms':ollama_ms})
                    if response.status_code not in (200,409):
                        print('Risultato non consegnato; nessun retry dell’inferenza.',flush=True)
                except httpx.HTTPError:
                    print('Risultato non consegnato; nessun retry dell’inferenza.',flush=True)


async def main():
    identity=json.loads((ROOT/'.local/s03/bridge.json').read_text())
    if identity['role']!='bridge':raise RuntimeError('Identità ponte non valida')
    key=identity['keys']['bridge']
    from gateway.runtime import ISOLATED
    if ISOLATED:raise RuntimeError('Il ponte deve essere eseguito sull’host, fuori dai container')
    print('Ponte locale attivo; nessun contenuto degli incarichi viene stampato.',flush=True)
    await asyncio.gather(worker(key),worker(key))


if __name__=='__main__':
    try:asyncio.run(main())
    except KeyboardInterrupt:pass
