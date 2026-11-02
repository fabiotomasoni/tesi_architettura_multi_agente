"""Un solo agente ADK generalista: strumenti diretti, nessuna delega a specialisti."""
import asyncio
from uuid import uuid4
from datetime import datetime,timezone
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from a2a.types import AgentCard,AgentCapabilities,AgentSkill
from gateway import runtime
from gateway.agent_contracts import BatchTask,MarketResult,TaxResult
from gateway.inference import MODELS
from gateway.a2a_egress import EgressDenied,authorized_task
from gateway.result_validation import MissingProvenanceError
from gateway.identity import AgentIdentityApp
from .market_work import perform as market_work
from .tax_work import perform as tax_work
if not runtime.SINGLE:raise RuntimeError('Generalista disponibile solo nel profilo single')
BOOT_ID=uuid4().hex


async def execute(task):
    result_type=MarketResult if task.scenario=='S-01' else TaxResult
    try:
        if task.deadline<=datetime.now(timezone.utc):raise TimeoutError()
        authorized_task(task)
        result=await (market_work if task.scenario=='S-01' else tax_work)(task)
    except MissingProvenanceError as error:
        partial_metrics = getattr(error,'work_metrics',{})
        status,code='unverified','missing_provenance'
    except EgressDenied as error:
        partial_metrics = getattr(error,'work_metrics',{})
        status,code='blocked','not_authorized'
    except TimeoutError as error:
        partial_metrics = getattr(error,'work_metrics',{})
        status,code='failed','timeout'
    except Exception as error:
        partial_metrics = getattr(error,'work_metrics',{})
        status,code='failed','execution_failed'
    else:
        result.measurements['agent_boot_id']=BOOT_ID
        return result
    return result_type(correlation_id=task.correlation_id,status=status,error_code=code,summary='Attività non completata; nessuna conclusione verificata.',limits=[],model=MODELS[task.scenario],measurements={'agent_boot_id':BOOT_ID,**partial_metrics})


class GeneralistAgent(BaseAgent):
    async def _run_async_impl(self,ctx):
        batch=BatchTask.model_validate_json(''.join(p.text or '' for p in ctx.user_content.parts))
        authorized_task(batch)
        results={}
        for task in batch.tasks:results[task.scenario]=(await execute(task)).model_dump(mode='json')
        import json
        yield Event(author=self.name,content=types.Content(role='model',parts=[types.Part(text=json.dumps({'correlation_id':str(batch.correlation_id),'results':results}))]))


card=AgentCard(name='generalist_agent',description='S-01 e S-02 nello stesso agente locale di laboratorio',version='0.1.0',url=runtime.AGENT_ENDPOINTS['BATCH'],capabilities=AgentCapabilities(streaming=False),default_input_modes=['text/plain'],default_output_modes=['text/plain'],skills=[AgentSkill(id='financial_analysis',name='Analisi finanziaria',description='Attività mercati e fiscalità con fonti fissate',tags=['S-01','S-02'])])
agent=GeneralistAgent(name='generalist_agent',description='Un solo agente per entrambe le attività')
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.server.tasks import InMemoryTaskStore
session_service=InMemorySessionService();task_store=InMemoryTaskStore()
runner=Runner(agent=agent,app_name='baseline',session_service=session_service)
from .request_lifecycle import SingleRequestApp, RequestExecutor
inner_app=to_a2a(agent,host='127.0.0.1',port=8001,agent_card=card,runner=runner,task_store=task_store, agent_executor_factory=lambda runner: RequestExecutor(runner=runner))


app=AgentIdentityApp(SingleRequestApp(inner_app, session_service, task_store, "baseline"),'BATCH')
