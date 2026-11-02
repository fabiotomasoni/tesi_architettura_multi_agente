"""Pipeline vincolata: MCP reale, sintesi tramite Ollama locale."""
import asyncio
from .work_metrics import observe_work, duration, count
from gateway.budgets import BUDGETS
from datetime import datetime, timezone
import json
import sys
from time import perf_counter

from .inference_client import request_summary
from .tool_client import request_tool, server_environment
from gateway.a2a_egress import EgressDenied
from gateway.inference import MODELS
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from gateway.agent_contracts import TaxTask, TaxResult, TaxEvidence

from gateway.ade_source import is_ade
from gateway.tax_evidence import verify_evidence

MODEL = MODELS['S-02']


@observe_work
async def perform(task: TaxTask, *, mcp_module: str | None = None, budget_seconds: float = BUDGETS.activity_seconds) -> TaxResult:
    seconds = (task.deadline - datetime.now(timezone.utc)).total_seconds()
    if seconds <= 0:
        raise ValueError('Incarico scaduto')
    async with asyncio.timeout(min(seconds, budget_seconds)):
        with duration('mcp_ms'):
            mcp_started = perf_counter()
            permit = await request_tool(task, mcp_module=mcp_module)
            if mcp_module is not None and mcp_module != permit.module:
                raise EgressDenied('Server MCP difforme dal catalogo')
            parameters = StdioServerParameters(command=sys.executable, args=['-m', permit.module], env=server_environment(task, permit))
            count('mcp_sessions_started')
            async with stdio_client(parameters) as streams:
                async with ClientSession(*streams) as client:
                    await client.initialize()
                    count('mcp_tool_calls')
                    result = await client.call_tool(permit.tool, permit.arguments)
                    count('mcp_tool_calls_completed')
                    if result.isError:
                        raise ValueError('Errore MCP')
                    evidence_text = result.content[0].text
            raw = json.loads(evidence_text)
            if raw == {'status':'blocked','error_code':'not_authorized'}:
                raise EgressDenied('Fonte rifiutata dal gateway')
            if raw == {'status':'failed','error_code':'timeout'}:
                raise TimeoutError('Timeout fonte gateway')
            evidence, source_digest = verify_evidence(raw, task.view)
            mcp_ms = (perf_counter() - mcp_started) * 1000
        ollama_started = perf_counter()
        with duration('inference_gateway_roundtrip_ms'):
            inference = await request_summary(task, evidence)
        summary = inference.summary
        return TaxResult(correlation_id=task.correlation_id, status='completed', evidence=evidence,
            summary=summary, model=MODEL, measurements={
                'source_content_verified':1, **({} if is_ade(evidence) else {'fixture_content_verified':1}), 'source_sha256':source_digest, 'mcp_ms':round(mcp_ms, 3), 'mcp_tool_calls':1,
                'ollama_ms':inference.ollama_ms, 'inference_gateway_roundtrip_ms':round((perf_counter()-ollama_started)*1000, 3), 'ollama_calls':1, 'inference_via_gateway':1,
                'prompt_tokens':inference.prompt_tokens, 'output_tokens':inference.output_tokens,
                'model_load_ms':inference.model_load_ms}, limits=[('Pubblicazione AdE verificata; nessuna spettanza personale accertata.' if is_ade(evidence) else 'Riferimenti fiscali inventati per test; nessuna normativa reale.'), 'Sintesi generata dal modello e non verificata.', 'Nessun confronto economico personalizzato eseguito.'])
