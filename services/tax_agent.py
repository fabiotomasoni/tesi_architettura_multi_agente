"""Agente ADK con delega A2A 0.3 e pipeline applicativa vincolata."""
import asyncio
from gateway.identity import AgentIdentityApp
from gateway.runtime import AGENT_ENDPOINTS
from gateway.a2a_egress import EgressDenied
from gateway.result_validation import MissingProvenanceError
from uuid import uuid4

BOOT_ID = uuid4().hex
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.genai import types
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from gateway.agent_contracts import TaxTask, TaxResult
from .tax_work import perform, MODEL


class TaxAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        text = ''.join(part.text or '' for part in ctx.user_content.parts)
        task = TaxTask.model_validate_json(text)
        try:
            result = await perform(task)
        except MissingProvenanceError:
            result = TaxResult(correlation_id=task.correlation_id,status='unverified',error_code='missing_provenance',evidence=None,
                summary='Fonte MCP non verificata; contenuto escluso.',limits=['Provenienza MCP obbligatoria mancante; nessun dato utilizzabile per conclusioni.'],model=MODEL,measurements={'provenance_verified':0})
        except EgressDenied:
            result = TaxResult(correlation_id=task.correlation_id,status='blocked',error_code='not_authorized',evidence=None,
                summary='Inferenza bloccata dal gateway.',limits=['Nessuna inferenza autorizzata disponibile.'],model=MODEL)
        except TimeoutError:
            result = TaxResult(correlation_id=task.correlation_id, status='failed', error_code='timeout',
                summary='Tempo massimo di elaborazione superato.', limits=['Nessun risultato disponibile entro la scadenza.'], model=MODEL)
        except Exception:
            result = TaxResult(correlation_id=task.correlation_id, status='failed',
                error_code='execution_failed', summary='Attività non completata: verificare MCP e Ollama locali.',
                limits=['Nessun risultato verificato disponibile.'], model=MODEL)
        result.measurements['agent_boot_id'] = BOOT_ID
        yield Event(author=self.name, content=types.Content(role='model', parts=[types.Part(text=result.model_dump_json())]))


card = AgentCard(name='tax_agent', description='Ricerca fiscale simulata S-02', version='0.1.0',
    url=AGENT_ENDPOINTS['S-02'], capabilities=AgentCapabilities(streaming=False),
    default_input_modes=['text/plain'], default_output_modes=['text/plain'],
    skills=[AgentSkill(id='tax_context', name='Fiscalità simulata', description='Fixture inventata, non normativa fiscale.', tags=['S-02'])])
agent = TaxAgent(name='tax_agent', description='Agente mercati locale con risultati simulati')

# Demo a richiesta singola: niente cronologia ADK o task A2A dopo la risposta.
# Le continuazioni multi-turno e tasks/get non fanno parte di questo incremento.
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from a2a.server.tasks import InMemoryTaskStore
session_service = InMemorySessionService()
task_store = InMemoryTaskStore()
runner = Runner(agent=agent, app_name='tax_demo', session_service=session_service)
inner_app = to_a2a(agent, host='127.0.0.1', port=8002, agent_card=card, runner=runner, task_store=task_store)


class SingleRequestApp:
    def __init__(self, inner):
        self.inner = inner
        self.lock = asyncio.Lock()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.inner(scope, receive, send)
        async with self.lock:
            try:
                await self.inner(scope, receive, send)
            finally:
                sessions = await session_service.list_sessions(app_name='tax_demo')
                for session in sessions.sessions:
                    await session_service.delete_session(app_name='tax_demo', user_id=session.user_id, session_id=session.id)
                async with task_store.lock:
                    task_store.tasks.clear()


app = AgentIdentityApp(SingleRequestApp(inner_app), 'S-02')
