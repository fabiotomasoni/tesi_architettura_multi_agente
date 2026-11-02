"""Pilota della traccia su A2A/MCP reali e ponte controllato, senza Ollama/Internet."""
import argparse
import asyncio
import json
import math
from pathlib import Path
from uuid import UUID

import httpx

if __package__:
    from .check_finalization import ControlledDemo, ROOT
else:
    from check_finalization import ControlledDemo, ROOT
from gateway.tracing import PHASES, METRICS, OUTCOMES, ERROR_CODES
from gateway.inference import MODELS


def validate(trace, *, organization='off', minimization='active'):
    """Controllo chiuso prima di esportare: nessun campo testuale libero."""
    allowed = {'trace_version','trace_id','gateway_boot_id','profile_created','profile_closed',
               'truncated','spans','configuration','summary','scope','semantics','retention_limits'}
    if set(trace)!=allowed or trace['trace_version']!='1.0.0':
        raise ValueError('Schema della traccia non riconosciuto')
    for key in ('trace_id','gateway_boot_id'):
        UUID(trace[key])
    for span in trace['spans']:
        if set(span)!={'span_id','parent_id','phase','scenario','correlation_id','start_ms','duration_ms','outcome','error_code','metrics'}:
            raise ValueError('Campi della fase non ammessi')
        for key in ('span_id','parent_id','correlation_id'):
            if span[key] is not None:UUID(span[key])
        if span['phase'] not in PHASES or span['scenario'] not in (None,'S-01','S-02','BATCH') or span['outcome'] not in OUTCOMES:
            raise ValueError('Categoria della fase non ammessa')
        if span['error_code'] is not None and span['error_code'] not in ERROR_CODES:
            raise ValueError('Codice di errore non ammesso')
        for value in (span['start_ms'],span['duration_ms']):
            if type(value) not in (int,float) or not math.isfinite(value) or value<0:
                raise ValueError('Durata non disponibile')
        if not set(span['metrics'])<=METRICS:
            raise ValueError('Metriche non ammesse')
        for value in span['metrics'].values():
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<0):
                raise ValueError('Metrica non numerica')
    if trace['scope']!='volatile_gateway_metadata_not_network_capture_or_client_receipt':
        raise ValueError('Perimetro della traccia non riconosciuto')
    # Configurazione/versioni/espressioni descrittive provengono dal gateway;
    # validare comunque l'intero JSON con il contratto canonico locale.
    from gateway.tracing import TraceStore
    from uuid import uuid4
    reference_store=TraceStore(uuid4().hex)
    reference=reference_store.snapshot(reference_store.create()[1])
    if organization not in {'off','single','multi'} or minimization not in {'active','disabled'}:
        raise ValueError('Configurazione sperimentale non ammessa')
    reference['configuration'].update(organization=organization, minimization=minimization)
    if (trace['configuration']!=reference['configuration'] or trace['semantics']!=reference['semantics']
            or trace['retention_limits']!=reference['retention_limits'] or set(trace['summary'])!=set(reference['summary'])):
        raise ValueError('Configurazione della traccia diversa dalla demo base')
    for name,value in trace['summary'].items():
        if name in {'all_spans_finished','trace_complete'}:
            if type(value) is not bool:raise ValueError('Stato della traccia non valido')
        elif value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<0):
            raise ValueError('Riepilogo della traccia non valido')
    if any(type(trace[k]) is not bool for k in ('profile_created','profile_closed','truncated')):
        raise ValueError('Stato del profilo non valido')
    return True


class TraceDemo(ControlledDemo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label='preflight'
        self.stage='health'
        self.rows=[]
        self.checks={}

    async def upload_case(self, case):
        self.stage='upload'
        response=await self.client.post('/sessions/pdf',files=[('files',(kind+'.pdf',
            (ROOT/'dataset/Documents'/f'{case}_{kind}.pdf').read_bytes(),'application/pdf')) for kind in ('mutuo','interessi')],
            data={'scenarios':['S-01','S-02']})
        response.raise_for_status();body=response.json()
        self.sessions.append(body['session_id'])
        if body.get('trace_id')!=response.headers.get('x-trace-id'):
            raise ValueError('ID traccia assente: ricostruire l’immagine aggiornata.')
        return body['session_id'],body['trace_id']

    async def claim(self):
        self.stage='claim_model'
        return await super().claim()

    async def deliver(self, job):
        self.stage='deliver_fixture'
        return await super().deliver(job)

    async def trace(self, identifier):
        self.stage='validate_trace'
        for _ in range(30):
            response=await self.client.get('/traces/'+identifier);response.raise_for_status()
            body=response.json()
            if body['summary']['all_spans_finished']:
                validate(body)
                return body
            await asyncio.sleep(.1)
        raise ValueError('Traccia ancora incompleta')


async def check(lab):
    boot=await lab.health()
    rows=lab.rows;checks=lab.checks;agent_boots=[]
    try:
        for label,case,count in [('nominal','C001',2),('partial','C006',1),('timeout','C001',2),('cancel','C001',2),('recovery','C001',2)]:
            lab.label=label
            sid,identifier=await lab.upload_case(case)
            pending=lab.start(sid)
            jobs=[]
            for _ in range(count):
                job=await lab.claim();jobs.append(job)
                if label=='cancel':continue
                if label=='timeout' and job['payload']['model']==MODELS['S-01']:
                    response=await lab.client.post('/_bridge/result/'+job['job_id'],headers=lab.headers,
                        json={'body':None,'error':'timeout','ollama_ms':None,'source_ms':None,
                              'execution':{'kind':'controlled_fixture','dispatch_attempts':0,'responses_observed':0}})
                else:
                    response=await lab.deliver(job)
                response.raise_for_status()
            if label=='cancel':
                lab.stage='cancel'
                response=await lab.client.delete('/sessions/'+sid)
                checks[label+'/acknowledged']=response.status_code==204
            lab.stage='analysis_result'
            response=await asyncio.wait_for(pending,10)
            body=response.json()
            expected={'nominal':'completed','partial':'partial','timeout':'partial','cancel':'cancelled','recovery':'completed'}[label]
            checks[label+'/outcome']=response.status_code==(409 if label=='cancel' else 200) and body.get('status')==expected
            if label in {'nominal','recovery'}:
                ids={s:a.get('result',{}).get('measurements',{}).get('agent_boot_id') for s,a in body.get('activities',{}).items()}
                agent_boots.append(ids)
            trace=await lab.trace(identifier)
            summary=trace['summary'];phases={s['phase'] for s in trace['spans']}
            checks[label+'/same_gateway']=UUID(trace['gateway_boot_id'])==UUID(boot)
            checks[label+'/trace_complete']=summary['trace_complete'] and not trace['truncated']
            checks[label+'/closed_profile']=trace['profile_closed'] and (await lab.client.delete('/sessions/'+sid)).status_code==404
            checks[label+'/phases']={'upload','pdf_prevalidation','extraction','privacy_context','profile_validation','policy_view','analysis','privacy_scan','prepare_task','delegate','tool_authorization','source_proxy','model_proxy','bridge_wait','cleanup','asgi_delivery'}<=phases
            if label!='cancel':
                checks[label+'/report_phases']={'report','presentation','verify_result'}<=phases
                checks[label+'/mcp_calls_reported']=summary['mcp_tool_calls_agent_reported']==count
            checks[label+'/a2a_attempts']=summary['a2a_message_dispatch_attempts']==count and summary['a2a_card_dispatch_attempts']==count
            checks[label+'/permits']=summary['tool_permits_issued']==count
            checks[label+'/model_proxy_calls']=summary['model_proxy_calls']==count
            checks[label+'/usage']=summary['prompt_tokens']==(None if label in {'timeout','cancel'} else count) and summary['output_tokens']==(None if label in {'timeout','cancel'} else count)
            if label=='cancel':
                checks[label+'/host_usage_unknown']=summary['host_http_dispatch_attempts'] is None
            else:
                checks[label+'/controlled_no_host_http']=summary['host_http_dispatch_attempts']==0 and summary['host_http_responses_observed']==0
            rows.append({'label':label,'case':case,'trace':trace})
        lab.label='rejected_input';lab.stage='upload'
        bad=await lab.client.post('/sessions/pdf',files={'files':('invalid.pdf',b'controlled invalid input')},data={'scenarios':['S-01']})
        identifier=bad.headers.get('x-trace-id')
        checks['rejected_input/trace_id']=bool(identifier) and bad.status_code==400
        if identifier:
            trace=await lab.trace(identifier)
            checks['rejected_input/no_profile']=not trace['profile_created'] and trace['summary']['trace_complete']
            rows.append({'label':'rejected_input','case':None,'trace':trace})
        checks['same_agents_after_faults']=len(agent_boots)==2 and agent_boots[0]==agent_boots[1] and all(agent_boots[0].values())
    finally:
        await lab.cleanup()
    return {'scope':'tracing_pilot_real_a2a_mcp_controlled_model_and_injected_timeout_not_actual_ollama_or_final_campaign',
            'checks':checks,'rows':rows,'passed':bool(checks) and all(checks.values())}


def failure_metadata(lab, error):
    """Categorie chiuse: mai stampare il testo di eccezioni HTTP o risposte."""
    labels={'preflight','nominal','partial','timeout','cancel','recovery','rejected_input'}
    stages={'health','upload','claim_model','deliver_fixture','cancel','analysis_result','validate_trace'}
    category='invalid_response'
    if isinstance(error,(TimeoutError,httpx.TimeoutException)):
        category='timeout'
    elif isinstance(error,httpx.HTTPStatusError):
        category='http_error'
    elif isinstance(error,httpx.HTTPError):
        category='transport_error'
    elif type(error) is ValueError:
        category={
            'Incarichi non ricevuti: controllare agenti e arresto del ponte ordinario.':'model_job_not_received',
            'Serve la demo isolata base con fonti simulate e ponte ordinario fermo.':'configuration_rejected',
            'Configurazione della traccia diversa dalla demo base':'trace_configuration_mismatch',
            'Traccia ancora incompleta':'trace_unfinished',
            'ID traccia assente: ricostruire l’immagine aggiornata.':'trace_id_missing',
        }.get(str(error),'invalid_response')
    result={'label':lab.label if lab.label in labels else 'preflight',
            'stage':lab.stage if lab.stage in stages else 'health','category':category}
    if isinstance(error,httpx.HTTPStatusError) and 100<=error.response.status_code<=599:
        result['http_status']=error.response.status_code
    return result


async def run_checked(lab, *, seconds=120):
    try:
        return await asyncio.wait_for(check(lab),seconds)
    except (ValueError,KeyError,TypeError,TimeoutError,httpx.HTTPError) as error:
        return {'scope':'tracing_pilot_incomplete_not_success_or_final_campaign',
                'checks':lab.checks,'rows':lab.rows,'failure':failure_metadata(lab,error),'passed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/trace_manual.json')
    args=parser.parse_args()
    if args.output.exists():parser.error('File già presente: scegliere un nome nuovo.')
    identity=json.loads((ROOT/'.local/s03/bridge.json').read_text())
    if identity.get('role')!='bridge':parser.error('Identità ponte non valida.')
    async def run():
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8080',timeout=35,trust_env=False,follow_redirects=False) as client:
            return await run_checked(TraceDemo(client,identity['keys']['bridge']))
    result=asyncio.run(run())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    for key,value in result['checks'].items():print(key+':',value)
    if 'failure' in result:
        failure=result['failure']
        print('Interruzione:',failure['label']+'/'+failure['stage'],'categoria:',failure['category'])
        if 'http_status' in failure:print('HTTP:',failure['http_status'])
        print('Prova incompleta: salvate solo evidenze raccolte, nessun successo dichiarato.')
    print('passed:',result['passed'])
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
