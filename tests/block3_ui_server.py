"""Server QA loopback: gateway e MCP reali, deleghe dirette e modello controllato.

Non è una configurazione comparativa o una prova di rete A2A/Docker. Non è
copiato nell'immagine dell'applicazione. Solo dati sintetici del template.
"""
import asyncio,json
import httpx
from gateway.app import create_app
from gateway.inference import OLLAMA_ENDPOINT
from services.market_work import perform as markets
from services.tax_work import perform as tax
import gateway.market_client as market_client,gateway.tax_client as tax_client
import services.tool_client as tools
import gateway.report_document as document
import gateway.report as report_module

mode={'name':'nominal','delay':2.0}
original=httpx.AsyncClient
class ControlledClient(original):
    async def post(self,url,*args,**kwargs):
        if str(url)!=OLLAMA_ENDPOINT:return await super().post(url,*args,**kwargs)
        payload=kwargs['json'];data=json.loads(payload['messages'][1]['content'])
        fiscal='tax-selection' in payload['messages'][0]['content']
        await asyncio.sleep(mode['delay'])
        if mode['name']=='fail_market' and not fiscal:return httpx.Response(503,request=httpx.Request('POST',url))
        content={'schema_version':'tax-selection-1' if fiscal else 'market-selection-1',
            'source_statement_ids':[s['statement_id'] for s in data['statements'] if s['kind']=='source'][:2],
            'context_statement_id':next(s['statement_id'] for s in data['statements'] if s['kind']=='context'),'explanation':''}
        return httpx.Response(200,request=httpx.Request('POST',url),json={'message':{'content':json.dumps(content)},'prompt_eval_count':1,'eval_count':1,'load_duration':0})
httpx.AsyncClient=ControlledClient
tools.GATEWAY_BASE='http://127.0.0.1:8005'
import services.inference_client as inference_client
inference_client.GATEWAY_ENDPOINT=tools.GATEWAY_BASE+'/internal/inference'
async def remote(task):
    return await (markets if task.scenario=='S-01' else tax)(task)
market_client.delegate=tax_client.delegate=remote
original_document=document.render_report_document
def presentation(report):
    if mode['name']=='no_presentation':raise ValueError('Controlled presentation failure')
    return original_document(report)
document.render_report_document=presentation
original_report=report_module.build_report
def build_report(*args,**kwargs):
    if mode['name']=='conflict_render_fixture':
        from gateway.comparisons import Observation
        kwargs['comparison_observations']=[Observation(observation_id='qa-'+suffix,quantity='aggregate_aar_nder',product='QA_SIMULATED_PRODUCT',period='2025-01',value=value,unit='percent_per_year',source_kind='agent',source_ref='simulated-presentation-fixture-'+suffix,verified=True) for suffix,value in [('a','3'),('b','4')]]
    report=original_report(*args,**kwargs)
    report['limits'].append('Verifica dell’interfaccia: risposte modello controllate, nessuna inferenza Ollama reale o prova A2A di rete.')
    if mode['name']=='conflict_render_fixture':report['consistency']['scope']='Conflitto sintetico del solo test di presentazione; non è un disaccordo prodotto dagli agenti reali.'
    return report
report_module.build_report=build_report
app=create_app()
@app.post('/qa/mode')
def configure(payload:dict):
    assert payload['name'] in {'nominal','fail_market','no_presentation','conflict_render_fixture'}
    assert 0<=payload.get('delay',2)<=5
    mode.update(name=payload['name'],delay=payload.get('delay',2))
    return {'scope':'ui_controlled_test_only'}
if __name__=='__main__':
    import uvicorn
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8005,log_level='critical',access_log=False))
    @app.post('/qa/stop')
    def stop():
        server.should_exit=True
        return {'stopping':True}
    server.run()
