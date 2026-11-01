"""Ponte host autenticato: ritira incarichi dal gateway, usa Ollama loopback e BCE su opt-in.

Non ascolta su alcuna porta. Due worker servono i due rami; nessun retry inferenza.
"""
import argparse
import asyncio
import json
from time import perf_counter
from pathlib import Path
import httpx
from gateway.inference import MODELS, PROMPTS
from gateway.agent_contracts import MarketView, TaxView
from gateway.ecb_source import (BRIDGE_JOB, REAL_MARKET_PROMPT, PublicObservation, fetch_ecb)
from gateway.market_evidence import verify_evidence as market
from gateway.tax_evidence import verify_evidence as tax
from gateway.ade_source import REAL_TAX_PROMPT, fetch_ade, source_job, publication, selected_quotes

BASE='http://127.0.0.1:8080'
OLLAMA='http://127.0.0.1:11434/api/chat'
ROOT=Path(__file__).resolve().parents[1]


def messages_prompt(payload):
    return payload.get('messages',[{}])[0].get('content')


def validate_payload(payload):
    # Controllo aggiuntivo del ponte: non è un proxy HTTP generico né una API Ollama.
    if not isinstance(payload,dict) or payload.get('model') not in MODELS.values():
        raise ValueError('Modello non autorizzato')
    from gateway import runtime
    if runtime.EXPERIMENT!='off':
        scenario=next((s for s in MODELS if messages_prompt(payload)==PROMPTS[s]),None)
        if scenario is None or payload['model']!=MODELS[scenario]:raise ValueError('Prompt sperimentale fuori catalogo')
    else:scenario=next(k for k,v in MODELS.items() if v==payload['model'])
    messages=payload['messages']
    evidence=json.loads(messages[1]['content'])
    lab_view=None
    if runtime.EXPERIMENT!='off':
        if set(evidence)!={'evidence','context'}:raise ValueError('Contesto sperimentale mancante')
        from gateway.lab_profile import FullFinancialView
        lab_view=(FullFinancialView if runtime.UNMINIMIZED else MarketView if scenario=='S-01' else TaxView).model_validate(evidence['context'])
        evidence=evidence['evidence']
    real=scenario=='S-01' and messages[0].get('content')==REAL_MARKET_PROMPT
    real_tax=scenario=='S-02' and messages[0].get('content')==REAL_TAX_PROMPT
    if real_tax:
        p=publication(evidence.get('tax_year'))
        if not any(evidence=={'source_id':'ade-annual-mortgage-v1','simulated':False,'tax_year':p['tax_year'],'publication_year':p['publication_year'],'quotes':selected_quotes(p['tax_year'],purpose)} for purpose in ('primary_home_purchase','renovation','other')):
            raise ValueError('Proiezione AdE difforme')
    elif real:
        parsed=PublicObservation.model_validate(evidence)
        if evidence!=parsed.model_dump(mode='json'):raise ValueError('Proiezione BCE non canonica')
    elif scenario=='S-01':
        from gateway.market_evidence import RATES
        rate=next((k for k,v in RATES.items() if v==evidence.get('annual_rate_percent')),None)
        view=MarketView(mortgage_type='not_specified',rate_type=rate,remaining_years_band={'lower_exclusive':0,'upper_inclusive':5})
        market(evidence,lab_view or view)
    else:
        view=TaxView(tax_year=evidence.get('tax_year'),purpose=evidence.get('purpose'))
        tax(evidence,lab_view or view)
    expected={'model':MODELS[scenario],'stream':False,'keep_alive':0,
              'options':{'num_ctx':4096,'num_predict':200,'temperature':0},
              'messages':[{'role':'system','content':REAL_TAX_PROMPT if real_tax else REAL_MARKET_PROMPT if real else PROMPTS[scenario]},
                          {'role':'user','content':messages[1]['content']}]}
    if scenario=='S-02' and runtime.EXPERIMENT=='off':expected['think']=False
    if payload!=expected:
        raise ValueError('Payload non autorizzato')
    return payload


async def execute_payload(payload, model, enable_ecb=False, enable_ade=False):
    from gateway import runtime
    if runtime.EXPERIMENT!='off' and payload.get('kind') in {'ade_tax_source','ecb_market_source'}:
        raise ValueError('Fonti reali vietate nella sperimentazione')
    if payload.get('kind')=='ade_tax_source':
        if not enable_ade or payload!=source_job(payload.get('tax_year')):
            raise ValueError('Richiesta AdE non autorizzata')
        body,source_ms=await fetch_ade(payload['tax_year'])
        return body,None,source_ms
    if payload.get('kind')=='ecb_market_source':
        if not enable_ecb or payload!=BRIDGE_JOB:
            raise ValueError('Fonte BCE non abilitata o richiesta difforme')
        evidence,source_ms=await fetch_ecb()
        return evidence.model_dump(mode='json'),None,source_ms
    payload=validate_payload(payload)
    started=perf_counter()
    response=await model.post(OLLAMA,json=payload)
    response.raise_for_status()
    if len(response.content)>60000:raise ValueError('Risposta troppo grande')
    return response.json(),round((perf_counter()-started)*1000,3),None


async def worker(key, enable_ecb=False, enable_ade=False):
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
                body=None;error=None;ollama_ms=None;source_ms=None
                try:
                    body,ollama_ms,source_ms=await execute_payload(job['payload'],model,enable_ecb,enable_ade)
                except (TimeoutError,httpx.TimeoutException):error='timeout'
                except Exception:error='unavailable'
                try:
                    response=await gateway.post(BASE+'/_bridge/result/'+job['job_id'],json={'body':body,'error':error,'ollama_ms':ollama_ms,'source_ms':source_ms})
                    if response.status_code not in (200,409):
                        print('Risultato non consegnato; nessun retry dell’inferenza.',flush=True)
                except httpx.HTTPError:
                    print('Risultato non consegnato; nessun retry dell’inferenza.',flush=True)


async def main(enable_ecb=False, enable_ade=False):
    from gateway import runtime
    if runtime.EXPERIMENT!='off' and (enable_ecb or enable_ade):raise RuntimeError('Nessuna fonte reale nel profilo comparativo')
    identity=json.loads((ROOT/('.local/baseline' if runtime.SINGLE else '.local/s03')/'bridge.json').read_text())
    if identity['role']!='bridge':raise RuntimeError('Identità ponte non valida')
    key=identity['keys']['bridge']
    from gateway.runtime import ISOLATED
    if ISOLATED:raise RuntimeError('Il ponte deve essere eseguito sull’host, fuori dai container')
    print('Ponte locale attivo; fonte BCE '+('abilitata' if enable_ecb else 'disabilitata')+'. Nessun contenuto degli incarichi viene stampato.',flush=True)
    print('Fonte AdE '+('abilitata' if enable_ade else 'disabilitata')+'.',flush=True)
    await asyncio.gather(worker(key,enable_ecb,enable_ade),worker(key,enable_ecb,enable_ade))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable-ecb',action='store_true',help='Abilita soltanto la richiesta pubblica BCE del catalogo.')
    parser.add_argument('--enable-ade',action='store_true',help='Abilita solo le due pubblicazioni fiscali annuali del catalogo.')
    args=parser.parse_args()
    try:asyncio.run(main(args.enable_ecb,args.enable_ade))
    except KeyboardInterrupt:pass
