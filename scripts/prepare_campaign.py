"""Prepara il manifest; approvazione esplicita separata, nessun esperimento avviato."""
import argparse,json,os,platform,shutil,subprocess,sys
from pathlib import Path
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.campaign_support import ROOT,VERSION,plan,source_files,runtime_files,read,write_new,digest,verify_bundle,verify_results


def command(args):
    r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=90)
    if r.returncode:raise ValueError('Controllo ambiente non riuscito; nessuna campagna avviata.')
    return r.stdout


def memory_capacity():
    try:
        if platform.system()=='Darwin':return int(command(['sysctl','-n','hw.memsize']).strip())
        if platform.system()=='Linux':return os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')
    except (ValueError,OSError,subprocess.SubprocessError):pass
    return None


def environment():
    import httpx
    from importlib.metadata import version
    docker=shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'
    info=json.loads(command([docker,'info','--format','{{json .}}']))
    tags=httpx.get('http://127.0.0.1:11434/api/tags',timeout=10,trust_env=False);tags.raise_for_status()
    model=next((x for x in tags.json()['models'] if x['name']=='llama3.2:3b'),None)
    if not model or not isinstance(model.get('digest'),str):raise ValueError('Modello comune non disponibile.')
    images={}
    for name in ('tesi-s03-app:local','tesi-s03-netguard:local'):
        image=json.loads(command([docker,'image','inspect',name]))[0]
        images[name]={'id':image['Id'],'repository_digests':image.get('RepoDigests') or []}
    code="""import hashlib,json,importlib.metadata as m
from pathlib import Path
files={}
for folder in ('gateway','services'):
 for p in Path(folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.js','.mjs','.css','.html','.json','.csv','.pdf','.yaml','.toml'}:files[p.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('pyproject.toml','requirements-lock.txt'):files[name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
print(json.dumps({'files':files,'python':__import__('platform').python_version(),'packages':{d.metadata['Name']:d.version for d in m.distributions() if d.metadata['Name']}}))"""
    inside=json.loads(command([docker,'run','--rm','--network','none','--read-only','--entrypoint','python','tesi-s03-app:local','-c',code]))
    if inside['files']!=runtime_files():raise ValueError('Immagine non allineata ai sorgenti: ricostruirla prima del manifest.')
    memory=memory_capacity()
    return {'host':{'physical_memory_capacity_bytes':memory,'processor':platform.processor(),'system':platform.system(),'release':platform.release(),'machine':platform.machine(),'python':platform.python_version(),'cpu_count':os.cpu_count()},
            'host_packages':{p:version(p) for p in ('fastapi','pydantic','langgraph','google-adk','a2a-sdk','mcp','httpx','pypdf')},
            'docker':{k:info.get(k) for k in ('ServerVersion','OSType','Architecture','NCPU','MemTotal','KernelVersion')},
            'images':images,'container_python':inside['python'],'container_packages':inside['packages'],
            'ollama':{'model':'llama3.2:3b','digest':model['digest'],'size':model.get('size'),'details':model.get('details'),
                      'version':httpx.get('http://127.0.0.1:11434/api/version',timeout=5,trust_env=False).json().get('version')},
            'generation':{'num_ctx':4096,'temperature':0,'keep_alive':0,'num_predict':{'S-01':768,'S-02':200},'seed':None},
            'budgets_seconds':{'activity':120,'model':90,'source':30,'transport_grace':5},
            'costs':{'observed_money_EUR':None,'api_tariff':None,'reason':'Local execution; electricity/hardware not measured, no API tariff invented.'}}


def prepare(folder, snapshot):
    folder=Path(folder)
    if folder.exists():raise ValueError('Cartella esistente: scegliere un nome nuovo.')
    artifacts={'plan.json':plan(),'pilot_plan.json':plan(pilot=True),
               'protocol.json':read(ROOT/'evaluation/protocol.json'),'registry.json':read(ROOT/'evaluation/test_registry.json'),
               'annotations.json':read(ROOT/'evaluation/annotations.json')}
    from scripts.check_evaluation_protocol import verify
    if not all(verify(artifacts['protocol.json'],artifacts['annotations.json']).values()):raise ValueError('Protocollo di riferimento non valido.')
    manifest={'version':VERSION,'status':'prepared_not_approved','sources':source_files(),
              'artifacts':{k:digest(v) for k,v in artifacts.items()},'environment':snapshot,
              'limitations':['Single evaluator; no inter-rater agreement.', 'Blinding removes labels, content can reveal condition.',
                             'No final result or score is implied by preparation.']}
    for name,value in artifacts.items():write_new(folder/name,value)
    write_new(folder/'manifest.json',manifest)
    return manifest


def approve(folder):
    errors=verify_bundle(folder,environment=environment())
    if errors:raise ValueError('Manifest da verificare: '+', '.join(errors))
    if verify_results(folder,pilot=True):raise ValueError('Artefatti del pilota assenti o modificati.')
    pilot=read(Path(folder)/'pilot/completion.json')
    if pilot.get('passed') is not True or pilot.get('manifest_sha256')!=digest(read(Path(folder)/'manifest.json')):
        raise ValueError('Pilota completo corrente non confermato. Nessuna approvazione registrata.')
    approval={'manifest_sha256':digest(read(Path(folder)/'manifest.json')), 'approved_by':'user',
              'scope':'frozen_protocol_and_final_execution','final_campaign_authorized':True}
    write_new(Path(folder)/'approval.json',approval)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','check','approve'])
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--approve-final-campaign',action='store_true');a=p.parse_args()
    try:
        if a.action=='prepare':
            m=prepare(a.directory,environment());print('Manifest preparato:',digest(m));print('Conteggi previsti:',plan()['counts'])
        elif a.action=='check':
            errors=verify_bundle(a.directory,environment=environment());print('Problemi:',len(errors))
            if errors:raise ValueError(', '.join(errors))
        else:
            if not a.approve_final_campaign:raise ValueError('Serve --approve-final-campaign, solo dopo revisione e ok esplicito dell’autore.')
            approve(a.directory);print('Approvazione del manifest registrata; nessuna esecuzione avviata.')
        print('Campagna avviata: False')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as e:p.error(str(e))

if __name__=='__main__':main()
