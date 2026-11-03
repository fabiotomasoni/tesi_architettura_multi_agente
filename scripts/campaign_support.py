"""Piano, manifest e raccolta del valutatore; nessun componente runtime li importa."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json, math, random, statistics

ROOT = Path(__file__).resolve().parents[1]
CELLS = ('single-active', 'single-disabled', 'multi-active', 'multi-disabled')
VERSION = 'thesis-campaign-1'
REVIEW_COLUMNS = ['evaluation_id','case_id','report_sha256','correctness','coverage','provenance','limits','critical_error','notes']


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write_new(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False); file.write('\n')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def plan(*, pilot=False):
    """Ordine bilanciato a blocchi: medesimo ordine dei casi nelle quattro celle."""
    cases = ['C001','C024','C006','C011','C016'] if pilot else [f'C{i:03}' for i in range(1,26)]
    blocks = []
    # Disegno Williams: posizioni ed effetti dell'ordine distribuiti; dieci
    # ripetizioni non sono un multiplo di quattro (sbilanciamento massimo uno).
    orders = [(0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1)]
    for rep in range(1, (1 if pilot else 10)+1):
        shuffled = cases.copy(); random.Random(2026+rep).shuffle(shuffled)
        for position, index in enumerate(orders[(rep-1)%4], 1):
            cell = CELLS[index]
            blocks.append({'id':f'r{rep:02}-{cell}', 'cell':cell, 'repetition':rep,
                           'position':position, 'cases':shuffled})
    registry = read(ROOT/'evaluation/test_registry.json')
    variants = [(c['id'],v['id']) for f in registry['families'] for c in f['additional_cycles'] for v in c['variants']]
    n = len(blocks); base = n*len(cases)
    return {'version':VERSION, 'scope':'pilot_not_final' if pilot else 'final_requires_separate_approval',
            'schedule_seed':2026, 'model_seed':None, 'blocks':blocks,
            'controlled_variants':[{'cycle':c,'variant':v} for c,v in variants],
            'counts':{'base_sessions':base, 'controlled_created_sessions':60*n,
                      'expected_created_sessions':base+60*n, 'rejected_upload_attempts':3*n,
                      'expected_upload_attempts':base+63*n, 'expected_delivered_reports':base+55*n},
            'counting':{'docker_per_block':{'created':54,'rejected_uploads':3,'delivered_reports':51},
                        'native_per_block':{'created':6,'rejected_uploads':0,'delivered_reports':4},
                        'native_variants':['ttl','delivery_asgi'],
                        'docker_variants':'existing_block2_suite_without_live_five_case_pilot',
                        'substitution_reference':'explicit_reuse_of_last_nominal_recovery_before_equivalent_then_restore',
                        'ratings':'all_actually_delivered_reports_once; no deduplication; absent reports not assigned zero'},
            'execution_levels':{'base':'Docker_with_actual_local_Ollama', 'controlled_docker':'Docker_with_controlled_model',
                                'ttl_and_direct_asgi':'native_ADK_A2A_MCP_controlled_model_not_container_isolation'},
            'limitations':['No model seed set by current payload; deterministic scheduling does not make LLM output deterministic.',
                            'Actual failures remain in the ledger; expected report count is not an assertion of success.']}


def source_files(root=ROOT):
    """Lista chiusa: include anche i driver, esclude credenziali, esiti e dati grezzi."""
    files = {}
    for folder in ('gateway','services','scripts','tests','evaluation','deployment'):
        for p in (root/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.js','.mjs','.css','.html','.json','.csv','.pdf','.yaml','.toml'}:
                files[p.relative_to(root).as_posix()] = sha256(p.read_bytes()).hexdigest()
    for pattern in ('compose*.yaml','*lock*','pyproject.toml','.dockerignore'):
        for p in root.glob(pattern):
            if p.is_file():files[p.name] = sha256(p.read_bytes()).hexdigest()
    for p in (root/'dataset/Documents').glob('*.pdf'):
        files[p.relative_to(root).as_posix()] = sha256(p.read_bytes()).hexdigest()
    return dict(sorted(files.items()))


def runtime_files(root=ROOT):
    return {k:v for k,v in source_files(root).items() if k.startswith(('gateway/','services/')) or k in {'pyproject.toml','requirements-lock.txt'}}


def verify_bundle(folder, *, environment=None):
    folder = Path(folder); manifest = read(folder/'manifest.json'); errors = []
    if manifest.get('version') != VERSION:errors.append('manifest_version')
    if manifest.get('sources') != source_files():errors.append('source_or_input_drift')
    for name in ('plan.json','pilot_plan.json','protocol.json','registry.json','annotations.json'):
        if manifest.get('artifacts',{}).get(name) != digest(read(folder/name)):errors.append(name+'_changed')
    if read(folder/'plan.json') != plan() or read(folder/'pilot_plan.json') != plan(pilot=True):errors.append('schedule_changed')
    if environment is not None and environment != manifest.get('environment'):errors.append('environment_or_model_drift')
    return errors


def check_approval(folder):
    folder=Path(folder)
    if not (folder/'approval.json').is_file():raise ValueError('Campagna finale non autorizzata: manca l’approvazione esplicita del manifest.')
    approval=read(folder/'approval.json')
    expected={'manifest_sha256':digest(read(folder/'manifest.json')), 'approved_by':'user',
              'scope':'frozen_protocol_and_final_execution', 'final_campaign_authorized':True}
    if approval != expected:raise ValueError('Approvazione assente, modificata o riferita a un altro manifest.')


def describe(values):
    known = [x for x in values if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)]
    return {'n':len(known),'missing':len(values)-len(known),
            'mean':statistics.mean(known) if known else None,
            'sample_variance':statistics.variance(known) if len(known)>1 else None}


def blind(report):
    """Rimuove solo metadati organizzativi, conservando tutti i contenuti valutabili.

    La cecità non è perfetta: testo e precisione possono suggerire la condizione.
    L'originale e il suo hash rimangono nel registro privato.
    """
    result=deepcopy(report)
    for key in ('policy_version','report_version','model_evaluation'):result.pop(key,None)
    for analysis in result.get('model_analyses',[]):analysis.pop('model',None)
    return result


class Collector:
    """Copie esplicite sul client del valutatore; nessun nuovo archivio nel gateway."""
    def __init__(self, folder, block, kind, *, annotations=None):
        self.folder=Path(folder); self.block=block; self.kind=kind; self.rows=[]; self.sessions={}
        self.context={'case':'C001','variant':'nominal'}
        self.annotations={c['case_id']:c for c in (annotations or read(ROOT/'evaluation/annotations.json'))['cases']}

    def capture(self, method, path, status, body, trace_id=None, attempt=None):
        if method=='POST' and path=='/sessions/pdf':
            row=attempt if attempt is not None else {'run_id':self.block['id']+'-'+self.kind+'-'+str(len(self.rows)+1).zfill(3),
                 'block_id':self.block['id'],'cell':self.block['cell'],'repetition':self.block['repetition'],
                 'kind':self.kind,'case':self.context.get('case','C001'),'variant':self.context.get('variant','nominal'),
                 'upload_http':status,'profile_created':status==201,'status':'input_rejected' if status!=201 else 'not_delivered',
                 'report_delivered':False,'trace_id':trace_id,'cleanup_verified':False}
            created=True if status==201 else False if status in {400,401,403,413,415,422} else None
            row.update(upload_http=status,profile_created=created,status='input_rejected' if created is False else 'not_delivered' if created else 'upload_reply_unavailable',trace_id=trace_id)
            if attempt is None:self.rows.append(row)
            if status==201:self.sessions[body['session_id']]=row
            return row
        parts=path.strip('/').split('/')
        if len(parts)==3 and parts[0]=='sessions' and parts[1] in self.sessions:
            row=self.sessions[parts[1]]
            if method=='POST' and parts[2]=='analysis' and not (status==409 and isinstance(body.get('detail'),dict) and body['detail'].get('error_code')=='analysis_already_running'):
                row.update(status=body.get('status','http_error'),analysis_http=status)
                report=body.get('report')
                if report is not None:
                    path=self.folder/'private/reports'/(row['run_id']+'.json')
                    write_new(path,report)
                    row.update(report_path=path.relative_to(self.folder).as_posix(), report_sha256=digest(report),report_delivered=True)
                    row['llm_contribution']={a['scenario']:{'status':a['status'],'selected_statements':len(a.get('selected_statements',[])),'comment_included':a['status']=='available','semantic_verified':a.get('semantic_verified') is True} for a in report.get('model_analyses',[])}
                for name in ('total_ms','report_ms','cleanup_ms','session_closed','experiment'):
                    if name in body:row[name]=body[name]
                row['activities']={s:{k:v for k,v in a.items() if k in {'status','error_code','phases'}} for s,a in body.get('activities',{}).items()}
                allowed={p+'_'+suffix for p in ('a2a_view','mcp_arguments','model_context') for suffix in ('bytes','fields','exact_amount_fields','exact_date_fields','exact_duration_fields')}
                row['disclosure']={s:{k:v for k,v in (a.get('result') or {}).get('measurements',{}).items() if k in allowed and isinstance(v,(int,float)) and not isinstance(v,bool)} for s,a in body.get('activities',{}).items()}
            elif method=='POST' and parts[2]=='views':
                scenario=body.get('scenario'); required=self.annotations[row['case']]['agent_utility_facts'].get(scenario)
                if scenario in {'S-01','S-02'}:
                    from scripts.evaluation_support import utility
                    row.setdefault('utility',{})[scenario]=utility(body.get('data',{}),required)
        if len(parts)==2 and parts[0]=='traces':
            for row in self.rows:
                if row.get('trace_id')==parts[1]:
                    row['trace']=body
                    row['cleanup_verified']=body.get('profile_closed') is True or body.get('profile_created') is False
        if method=='DELETE' and len(parts)==2 and parts[0]=='sessions' and parts[1] in self.sessions and status==404:
            self.sessions[parts[1]]['cleanup_verified']=True

    def async_factory(self, context):
        import httpx
        collector=self
        class ObservedClient(httpx.AsyncClient):
            async def send(self, request, *args, **kwargs):
                attempt=None
                if request.method=='POST' and request.url.host=='127.0.0.1' and request.url.port==8080 and request.url.path=='/sessions/pdf':
                    collector.context=dict(context())
                    attempt=collector.capture('POST','/sessions/pdf',None,{},None)
                    attempt.update(profile_created=None,status='upload_reply_unavailable',cleanup_verified=False)
                response=await super().send(request,*args,**kwargs)
                if request.url.host=='127.0.0.1' and request.url.port==8080 and request.url.path.startswith(('/sessions','/traces')):
                    await response.aread()
                    try:body=response.json()
                    except ValueError:body={}
                    collector.context=dict(context())
                    collector.capture(request.method,request.url.path,response.status_code,body,response.headers.get('x-trace-id'),attempt=attempt)
                    if request.method=='POST' and request.url.path.endswith('/analysis'):
                        identifier=response.headers.get('x-trace-id')
                        if identifier:
                            # Questa lettura attraversa lo stesso osservatore, mai prompt o token.
                            await self.get('/traces/'+identifier)
                return response
        return ObservedClient

    def finish(self, *, procedure_passed):
        # Nei driver relay/cancel/crash i tre ingressi sono prima, guasto, recupero.
        for variant in ('cancel','delivery_relay','crash','ttl','delivery_asgi'):
            rows=[r for r in self.rows if r['variant']==variant]
            for index,row in enumerate(rows):
                row['role']=('before','fault','recovery')[index] if len(rows)==3 else 'unconfirmed'
                if row['role']=='fault':
                    row['report_delivered']=False
                    row['absence_reason']='controlled_delivery_fault' if variant.startswith('delivery') else 'cancelled_or_expired' if variant in {'cancel','ttl'} else 'gateway_forced_exit'
        for row in self.rows:
            row['procedure_passed']=procedure_passed
            row['model_mode']=('actual_ollama' if row.get('checks',{}).get('actual_ollama_execution') is True else 'unconfirmed') if self.kind=='base' else 'controlled_fixture' if procedure_passed else 'controlled_expected_unconfirmed'
            row['execution_level']='native_application_not_container_isolation' if self.kind=='native' else 'docker'
            if row['profile_created'] is False:row['cleanup_verified']=True
        return self.rows


def reference_checks(report, annotation):
    """Confronto indipendente coi fatti rivisti e calcoli di riferimento del valutatore."""
    from decimal import Decimal,InvalidOperation
    checks={};facts={k:v for section in report['document_data'] for k,v in section['facts'].items()}
    for key,expected in annotation['facts'].items():
        actual=facts.get(key,{})
        matches=actual.get('status')==expected['status']
        if expected['status']=='validated':
            matches &= actual.get('unit')==expected['unit'] and actual.get('period')==expected['period']
            try:
                matches &= actual.get('value')==expected['value'] if expected['unit']=='category' else Decimal(str(actual.get('value')))==Decimal(str(expected['value']))
            except (InvalidOperation,ValueError):matches=False
        checks['reference_fact/'+key]=bool(matches)
    def amount(actual,expected):
        try:return abs(Decimal(str(actual))-Decimal(str(expected)))<=Decimal('0.01')
        except (InvalidOperation,ValueError):return False
    calculations=annotation['expected_calculations']
    for expected_key,section,scenario in [('contract','mortgage_contract_analysis','contract_rate_scenario'),('alternative_fixture','mortgage_comparison','simulated_rate_scenario')]:
        if expected_key not in calculations:continue
        actual=(report.get(section) or {}).get(scenario,{})
        for want,got in [('monthly_payment','theoretical_monthly_payment'),('total_payments','theoretical_total_payments'),('remaining_interest','theoretical_total_interest')]:
            checks['reference_calculation/'+expected_key+'/'+want]=amount(actual.get(got),calculations[expected_key][want])
    if 'hypothetical_interest_share' in calculations:
        checks['reference_calculation/hypothetical_share']=amount((report.get('tax_application') or {}).get('hypothetical_allocation',{}).get('amount_EUR'),calculations['hypothetical_interest_share'])
    return checks


def result_hashes(folder):
    folder=Path(folder)
    return {p.relative_to(folder).as_posix():sha256(p.read_bytes()).hexdigest()
            for p in sorted((folder/'private').rglob('*.json')) if p.name!='review_mapping.json'}


def verify_results(bundle, *, pilot=False):
    bundle=Path(bundle);folder=bundle/('pilot' if pilot else 'final')
    completion=read(folder/'completion.json');schedule=read(bundle/('pilot_plan.json' if pilot else 'plan.json'))
    errors=[]
    if completion.get('manifest_sha256')!=digest(read(bundle/'manifest.json')):errors.append('manifest_binding')
    if completion.get('blocks')!=len(schedule['blocks']):errors.append('block_count')
    if completion.get('private_sha256')!=result_hashes(folder):errors.append('result_artifact_drift')
    for block in schedule['blocks']:
        path=folder/'private/blocks'/(block['id']+'.json')
        if not path.is_file() or read(path).get('block')!=block:errors.append('block_missing_or_changed')
    return errors


def require_cold_models(status):
    if status.get('models')!=[]:
        raise ValueError('Ollama deve iniziare senza modelli caricati: controllare ollama ps e fermare le altre elaborazioni prima del pilota.')


def actual_model_receipts(trace, expected_calls):
    waits=[s for s in trace.get('spans',[]) if s['phase']=='bridge_wait']
    return len(waits)==expected_calls and all(s.get('outcome')=='completed' and s['metrics'].get('execution_controlled_fixture')==0 and s['metrics'].get('host_http_dispatch_attempts')==1 and s['metrics'].get('host_http_responses_observed')==1 for s in waits)
