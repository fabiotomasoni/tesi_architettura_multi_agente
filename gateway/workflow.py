"""Orchestrazione S-01 in memoria: nessuna policy duplicata o persistenza."""
import asyncio
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import TypedDict
from uuid import uuid4

from fastapi import HTTPException
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context

from .agent_contracts import MarketTask, MarketView, MarketResult
from .a2a_egress import EgressDenied


class State(TypedDict, total=False):
    task: MarketTask
    result: MarketResult
    status: str
    error_code: str | None
    phases: list[dict]


async def run_workflow(request_view, delegate, cleanup, *, task_type=MarketTask, view_type=MarketView, result_type=MarketResult, scope="market_rate_context"):
    """Callback locali gateway; lo stato non contiene profilo esatto né PDF."""
    started = perf_counter()
    phases = []
    outcome = {'status':'failed', 'error_code':'workflow_error'}

    def phase(name, began, status):
        phases.append({'phase':name, 'duration_ms':round((perf_counter()-began)*1000,3), 'status':status})

    def prepare(state):
        began = perf_counter()
        try:
            permitted = request_view()
            task = task_type(purpose=scope,correlation_id=uuid4(),deadline=datetime.now(timezone.utc)+timedelta(seconds=120),
                              view=view_type.model_validate(permitted['data']))
        except HTTPException as exc:
            status = 'blocked' if exc.status_code in {403,409} else 'failed'
            phase('request_view',began,status)
            return {'status':status,'error_code':'input_not_ready' if exc.status_code==409 else 'not_authorized'}
        phase('request_view',began,'completed')
        return {'task':task,'status':'ready','error_code':None}

    async def dispatch(state):
        began=perf_counter()
        try:
            # Limite globale: include Card e delega, non solo la fase del modello.
            async with asyncio.timeout(125):
                result=await delegate(state['task'])
        except EgressDenied:
            phase('delegate_a2a',began,'blocked')
            return {'status':'blocked','error_code':'not_authorized'}
        except TimeoutError:
            phase('delegate_a2a',began,'failed')
            return {'status':'failed','error_code':'timeout'}
        except Exception:
            phase('delegate_a2a',began,'failed')
            return {'status':'failed','error_code':'delegation_failed'}
        phase('delegate_a2a',began,'completed')
        return {'result':result}

    def verify(state):
        began=perf_counter()
        try:
            result=result_type.model_validate(state['result'])
            if result.correlation_id != state['task'].correlation_id:
                raise ValueError('Correlazione errata')
            if result.status=='failed' and result.evidence is not None:
                raise ValueError('Evidenza in risultato fallito')
        except Exception:
            phase('verify_result',began,'failed')
            return {'status':'failed','error_code':'invalid_result'}
        phase('verify_result',began,'completed')
        return {'status':result.status,'error_code':result.error_code}

    graph=StateGraph(State)
    graph.add_node('request_view',prepare)
    graph.add_node('delegate_a2a',dispatch)
    graph.add_node('verify_result',verify)
    graph.add_edge(START,'request_view')
    graph.add_conditional_edges('request_view',lambda s:'delegate_a2a' if s['status']=='ready' else END)
    graph.add_conditional_edges('delegate_a2a',lambda s:'verify_result' if 'result' in s else END)
    graph.add_edge('verify_result',END)
    try:
        # Anche se l'ambiente abilita LangSmith, questa invocazione non esporta tracce.
        with tracing_context(enabled=False):
            state=await graph.compile(checkpointer=None).ainvoke({},config={'callbacks':[]})
        outcome={'status':state['status'],'error_code':state.get('error_code')}
        if 'result' in state and state['error_code']!='invalid_result':
            outcome['result']=state['result'].model_dump(mode='json')
    finally:
        began=perf_counter()
        cleanup()
        phase('cleanup',began,'completed')
    return {**outcome,'workflow':'S-01-langgraph-v1','phases':phases,
            'session_closed':True,'total_ms':round((perf_counter()-started)*1000,3)}
