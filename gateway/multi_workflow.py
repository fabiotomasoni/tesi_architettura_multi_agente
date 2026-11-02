"""Esecuzione concorrente dei soli scenari richiesti, finalizzazione unica."""
import asyncio
from time import perf_counter
from langsmith import tracing_context
from .workflow import run_workflow
from .agent_contracts import TaxTask, TaxView, TaxResult
from .tracing import Span
from .budgets import BUDGETS


async def run_analysis(scenarios, request_view, delegates, cleanup, make_report=None):
    from . import runtime
    from datetime import datetime,timedelta,timezone
    shared_deadline=datetime.now(timezone.utc)+timedelta(seconds=BUDGETS.activity_seconds) if runtime.EXPERIMENT!='off' else None
    started=perf_counter()
    async def branch(scenario):
        options={} if scenario=='S-01' else {'task_type':TaxTask,'view_type':TaxView,'result_type':TaxResult,'scope':'tax_context'}
        result=await run_workflow(lambda:request_view(scenario),delegates[scenario],lambda:None,deadline=shared_deadline,**options)
        # I subgrafi non possiedono la sessione: solo il coordinatore la chiude.
        result.pop('session_closed',None)
        result['phases']=[p for p in result['phases'] if p['phase']!='cleanup']
        return result
    try:
        with tracing_context(enabled=False):
            from . import runtime
            if runtime.EXPERIMENT=='multi':
                results=[await branch(s) for s in scenarios]
            else:
                async with asyncio.TaskGroup() as group:
                    running=[group.create_task(branch(s)) for s in scenarios]
                results=[task.result() for task in running]
        tasks=dict(zip(scenarios,results))
        completed=sum(r['status']=='completed' for r in results)
        status='completed' if completed==len(results) else 'partial' if completed else 'blocked' if all(r['status']=='blocked' for r in results) else 'unverified' if any(r['status']=='unverified' for r in results) else 'failed'
        report=None
        report_ms=0.0
        if make_report is not None:
            began=perf_counter()
            with Span('report'):
                report=make_report(tasks,status)
            report_ms=(perf_counter()-began)*1000
            # I riepiloghi tecnici non riespongono prosa esclusa dal report.
            for activity in tasks.values():
                result=activity.get('result')
                if result is not None:
                    result['summary']='Prosa del modello esclusa; consultare la sintesi deterministica del report.'

    finally:
        began=perf_counter()
        cleanup()
        cleanup_ms=(perf_counter()-began)*1000
    return {'workflow':'multi-langgraph-v1','status':status,'activities':tasks,'session_closed':True,
            'report':report,'report_ms':round(report_ms,3),'cleanup_ms':round(cleanup_ms,3),'total_ms':round((perf_counter()-started)*1000,3),
            'limits':['Fonti classificate nel report; nessuna conclusione definitiva di convenienza o spettanza fiscale.']}
