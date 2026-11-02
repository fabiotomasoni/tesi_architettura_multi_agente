"""V-06: standard → MCP equivalente → standard; solo gateway riconfigurato."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

if __package__:
    from .check_finalization import ControlledDemo, DockerGateway, ROOT, wait_ready
    from .check_report_provenance import verify as provenance
    from .check_mortgage import verify as mortgage
    from .check_tax_application import verify as tax
else:
    from check_finalization import ControlledDemo, DockerGateway, ROOT, wait_ready
    from check_report_provenance import verify as provenance
    from check_mortgage import verify as mortgage
    from check_tax_application import verify as tax

CASES = ['C001','C024','C006','C011','C016']
MODULES = {'standard':'services.rates_mcp','equivalent':'services.rates_mcp_equivalent'}
NAMES = {'standard':'authorized_market_rates','equivalent':'equivalent_market_rates'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def normalized(value):
    """Conserva tutti i campi; sostituisce solo gli ID allocati ai PDF con i digest."""
    identifiers = {}
    def collect(item):
        if isinstance(item,dict):
            if 'document_id' in item:
                doc = item['document_id'];sha = item.get('document_sha256')
                if not isinstance(doc,str) or not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):
                    raise ValueError('Origine documentale priva di digest verificabile')
                replacement = 'pdf-sha256:'+sha
                if doc in identifiers and identifiers[doc]!=replacement:
                    raise ValueError('ID documentale associato a due PDF')
                identifiers[doc] = replacement
            for child in item.values():collect(child)
        elif isinstance(item,list):
            for child in item:collect(child)
    collect(value)
    def replace(item):
        if isinstance(item,dict):return {key:replace(child) for key,child in item.items()}
        if isinstance(item,list):return [replace(child) for child in item]
        if isinstance(item,str):
            for doc,sha in identifiers.items():item=item.replace(doc,sha)
        return item
    return replace(value)


def code_digest():
    paths = [p for directory in ['gateway','services'] for p in (ROOT/directory).rglob('*') if p.suffix in {'.py','.html'}]
    paths += [ROOT/name for name in ['pyproject.toml','requirements-lock.txt','compose.isolated.yaml','compose.substitution.yaml']]
    return digest({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})


async def schema(module):
    async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m',module])) as streams:
        async with ClientSession(*streams) as client:
            initialized = await client.initialize()
            tools = await client.list_tools()
    return {'server_name':initialized.serverInfo.name,'tool_contracts':[t.model_dump(mode='json') for t in tools.tools]}


class SubstitutionController(DockerGateway):
    async def configure(self, implementation):
        command = list(self.compose)
        if implementation=='equivalent':command += ['-f','compose.substitution.yaml']
        elif implementation!='standard':raise ValueError('Implementazione non autorizzata')
        await self.run(command+['up','-d','--no-build','--no-deps','gateway'])

    async def images(self):
        result = {}
        for role in ['gateway','markets','tax']:
            cid = await self.run(self.compose+['ps','-q',role])
            if not cid or '\n' in cid:raise ValueError('Servizi base non disponibili')
            data = json.loads(await self.run([self.docker,'inspect',cid]))[0]
            result[role] = data['Image']
        if len(set(result.values()))!=1:
            raise ValueError('I tre servizi devono usare la stessa immagine aggiornata')
        return result


class SubstitutionDemo(ControlledDemo):
    async def upload_case(self, case):
        from gateway.lab_corpus import PDF_CASES
        documents = {kind:(ROOT/'dataset/Documents'/f'{case}_{kind}.pdf').read_bytes() for kind in ['mutuo','interessi']}
        hashes = {kind:hashlib.sha256(body).hexdigest() for kind,body in documents.items()}
        if any(PDF_CASES.get(value)!=case for value in hashes.values()):
            raise ValueError('Dataset diverso dal corpus sintetico fissato')
        response = await self.client.post('/sessions/pdf',files=[('files',(kind+'.pdf',body,'application/pdf')) for kind,body in documents.items()],
            data={'scenarios':['S-01','S-02']})
        response.raise_for_status();data=response.json()
        sid = data['session_id'];self.sessions.append(sid)
        return sid,data['profile'],hashes

    async def run_case(self, case, implementation):
        sid,profile,pdfs = await self.upload_case(case)
        expected = {'S-01':'blocked' if case in {'C006','C016'} else 'completed','S-02':'blocked' if case=='C011' else 'completed'}
        pending = self.start(sid)
        for _ in range(sum(value=='completed' for value in expected.values())):
            response = await self.deliver(await self.claim());response.raise_for_status()
        response = await pending;response.raise_for_status();body=response.json()
        checks = {'activities_expected':{s:a['status'] for s,a in body['activities'].items()}==expected,
                  'session_closed':body.get('session_closed') is True}
        await self.closed(sid,checks,'cleanup')
        report = body['report']
        count,problems = provenance(report,ROOT/'dataset/Documents')
        checks['document_provenance'] = count>0 and not problems
        checks.update(mortgage(report));checks.update(tax(report))
        measurements = {}
        for scenario,activity in body['activities'].items():
            if activity['status']!='completed':continue
            values = activity['result']['measurements']
            for key in ['a2a_requests','mcp_tool_calls','ollama_calls','gateway_tool_authorized','gateway_source_completed','gateway_inference_completed','gateway_source_receipt_verified','source_content_verified']:
                checks[scenario+'/'+key] = values.get(key)==1
            module = MODULES[implementation] if scenario=='S-01' else 'services.tax_mcp'
            checks[scenario+'/authorized_module'] = values.get('gateway_tool_module')==module
            if scenario=='S-01':checks[scenario+'/server_initialized'] = values.get('mcp_server_name')==NAMES[implementation] and bool(values.get('mcp_server_version'))
            checks[scenario+'/boot_present'] = bool(values.get('agent_boot_id'))
            measurements[scenario] = {key:values.get(key) for key in ['agent_boot_id','gateway_tool_module','mcp_server_name','mcp_server_version','source_sha256','tool_catalog_version']}
        # Il documento leggibile deriva dallo stesso report: confronto completo.
        snapshot = normalized({'report':report,'document_html':body.get('report_document_html')})
        checks['readable_document_present'] = isinstance(body.get('report_document_html'),str) and bool(body['report_document_html'])
        return {'case':case,'checks':checks,'passed':all(value is True for value in checks.values()),
                'pdf_sha256':pdfs,'profile_sha256':digest(normalized(profile)),
                'complete_report_sha256':digest(snapshot),'measurements':measurements}


def compare(phases):
    if set(phases)!={'reference','replacement','restored'}:raise ValueError('Servono tutte e tre le fasi')
    reference,replacement,restored=(phases[key] for key in ['reference','replacement','restored'])
    checks = {
        'same_source_code':len({phase['code_sha256'] for phase in phases.values()})==1,
        'same_images':reference['images']==replacement['images']==restored['images'],
        'same_other_settings':reference['settings']==replacement['settings']==restored['settings'],
        'gateway_reconfigured_each_phase':len({phase['gateway_boot_id'] for phase in phases.values()})==3,
        'implementations_selected': [phase['implementation'] for phase in [reference,replacement,restored]]==['standard','equivalent','standard'],
    }
    records = []
    for phase in [reference,replacement,restored]:
        indexed = {row['case']:row for row in phase['rows']}
        if set(indexed)!=set(CASES) or len(phase['rows'])!=len(CASES):raise ValueError('Casi mancanti o duplicati')
        records.append(indexed)
    for case in CASES:
        rows = [phase[case] for phase in records]
        checks[case+'/runs_passed'] = all(row['passed'] and all(value is True for value in row['checks'].values()) for row in rows)
        for key in ['pdf_sha256','profile_sha256','complete_report_sha256']:
            checks[case+'/'+key+'_unchanged'] = rows[0][key]==rows[1][key]==rows[2][key]
        for scenario in rows[0]['measurements']:
            values = [row['measurements'].get(scenario,{}) for row in rows]
            checks[case+'/'+scenario+'/same_agent_boot'] = len({v.get('agent_boot_id') for v in values})==1 and bool(values[0].get('agent_boot_id'))
            checks[case+'/'+scenario+'/same_source_digest'] = len({v.get('source_sha256') for v in values})==1 and bool(values[0].get('source_sha256'))
    return checks


async def check(lab, controller):
    await lab.health()
    health = (await lab.client.get('/health')).json()
    if health.get('market_tool_implementation')!='standard' or health.get('tool_catalog_version')!='0.4.0':
        raise ValueError('Avviare la demo base con l’immagine aggiornata e lo strumento standard')
    schemas = {key:await schema(module) for key,module in MODULES.items()}
    checks = {'distinct_servers':schemas['standard']['server_name']!=schemas['equivalent']['server_name'],
              'expected_server_names':all(schemas[key]['server_name']==NAMES[key] for key in MODULES),
              'same_mcp_tool_contract':schemas['standard']['tool_contracts']==schemas['equivalent']['tool_contracts']}
    if not all(checks.values()):raise ValueError('Il contratto MCP sostitutivo non è equivalente')
    phases = {}
    changed = False
    try:
        for phase,implementation in [('reference','standard'),('replacement','equivalent'),('restored','standard')]:
            if phase!='reference':
                changed = True
                await controller.configure(implementation)
            boot = await wait_ready(lab)
            current = (await lab.client.get('/health')).json()
            if current.get('market_tool_implementation')!=implementation:raise ValueError('Configurazione gateway inattesa')
            rows = []
            for case in CASES:
                row = await lab.run_case(case,implementation);rows.append(row)
                print(phase,case,'passed:',row['passed'],flush=True)
            phases[phase] = {'implementation':implementation,'gateway_boot_id':boot,
                'settings':{k:v for k,v in current.items() if k not in {'gateway_boot_id','market_tool_implementation'}},
                'images':await controller.images(),'code_sha256':code_digest(),'rows':rows}
            if phase=='restored':changed=False
        checks.update(compare(phases))
    finally:
        try:
            if changed:
                await controller.configure('standard')
                await wait_ready(lab)
        finally:
            await lab.cleanup()
    return {'scope':'V06_one_equivalent_market_mcp_with_controlled_model_not_general_agent_substitution_or_final_campaign',
            'checks':checks,'phases':phases,'passed':all(value is True for value in checks.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'runs/substitution_manual.json')
    args = parser.parse_args()
    if args.output.exists():parser.error('File già presente: scegliere un nome nuovo.')
    identity=json.loads((ROOT/'.local/s03/bridge.json').read_text())
    if identity.get('role')!='bridge':parser.error('Identità del ponte non valida.')
    async def run():
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8080',timeout=35,trust_env=False,follow_redirects=False) as client:
            return await asyncio.wait_for(check(SubstitutionDemo(client,identity['keys']['bridge']),SubstitutionController()),240)
    try:data=asyncio.run(run())
    except (ValueError,TimeoutError,httpx.HTTPError) as error:
        if type(error) is ValueError:parser.error(str(error))
        parser.error('Prova non completata: controllare servizi e ponte ordinario fermo. Nessun successo registrato.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')
    for name,value in data['checks'].items():print(name+':',value)
    print('passed:',data['passed'])
    raise SystemExit(0 if data['passed'] else 1)


if __name__=='__main__':main()
