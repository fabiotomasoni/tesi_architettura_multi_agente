"""Pipeline vincolata: MCP reale, sintesi tramite Ollama locale."""
import asyncio
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
from gateway.agent_contracts import MarketTask, MarketResult, RateEvidence

from gateway.market_evidence import verify_evidence

MODEL = MODELS['S-01']


async def perform(task: MarketTask, *, mcp_module: str | None = None, budget_seconds: float = 120) -> MarketResult:
    seconds = (task.deadline - datetime.now(timezone.utc)).total_seconds()
    if seconds <= 0:
        raise ValueError('Incarico scaduto')
    async with asyncio.timeout(min(seconds, budget_seconds)):
        mcp_started = perf_counter()
        permit = await request_tool(task, mcp_module=mcp_module)
        if mcp_module is not None and mcp_module != permit.module:
            raise EgressDenied('Server MCP difforme dal catalogo')
        parameters = StdioServerParameters(command=sys.executable, args=['-m', permit.module], env=server_environment(task, permit))
        async with stdio_client(parameters) as streams:
            async with ClientSession(*streams) as client:
                await client.initialize()
                result = await client.call_tool(permit.tool, permit.arguments)
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
        inference = await request_summary(task, evidence)
        summary = inference.summary
        return MarketResult(correlation_id=task.correlation_id, status='completed', evidence=evidence,
            summary=summary, model=MODEL, measurements={
                'fixture_content_verified':1, 'source_sha256':source_digest, 'mcp_ms':round(mcp_ms, 3), 'mcp_tool_calls':1,
                'ollama_ms':inference.ollama_ms, 'inference_gateway_roundtrip_ms':round((perf_counter()-ollama_started)*1000, 3), 'ollama_calls':1, 'inference_via_gateway':1,
                'prompt_tokens':inference.prompt_tokens, 'output_tokens':inference.output_tokens,
                'model_load_ms':inference.model_load_ms}, limits=['Fonte interamente simulata; nessuna quotazione reale.', 'Sintesi generata dal modello e non verificata.', 'Nessun confronto economico personalizzato eseguito.'])
