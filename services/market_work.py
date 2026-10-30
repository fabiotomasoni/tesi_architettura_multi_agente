"""Pipeline vincolata: MCP reale, sintesi tramite Ollama locale."""
import asyncio
from datetime import datetime, timezone
import json
import sys
from time import perf_counter

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from gateway.agent_contracts import MarketTask, MarketResult, RateEvidence

from gateway.market_evidence import verify_evidence

MODEL = 'llama3.2:3b'


async def perform(task: MarketTask, *, mcp_module: str = 'services.rates_mcp', budget_seconds: float = 120) -> MarketResult:
    seconds = (task.deadline - datetime.now(timezone.utc)).total_seconds()
    if seconds <= 0:
        raise ValueError('Incarico scaduto')
    async with asyncio.timeout(min(seconds, budget_seconds)):
        mcp_started = perf_counter()
        parameters = StdioServerParameters(command=sys.executable, args=['-m', mcp_module])
        async with stdio_client(parameters) as streams:
            async with ClientSession(*streams) as client:
                await client.initialize()
                result = await client.call_tool('lookup_rates', task.view.model_dump(mode='json'))
                if result.isError:
                    raise ValueError('Errore MCP')
                evidence, source_digest = verify_evidence(json.loads(result.content[0].text), task.view)
        mcp_ms = (perf_counter() - mcp_started) * 1000
        ollama_started = perf_counter()
        async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
            response = await client.post('http://127.0.0.1:11434/api/chat', json={
                'model': MODEL, 'stream': False, 'keep_alive': 0,
                'options': {'num_ctx':4096, 'num_predict':200, 'temperature':0},
                'messages': [{'role':'system','content':'Scrivi in italiano due frasi che descrivono la fixture simulata. Non dare consigli, non dichiarare convenienza e non inventare informazioni. Specifica che non sono dati di mercato reali.'},
                             {'role':'user','content':json.dumps(evidence.model_dump(mode='json'))}]})
            response.raise_for_status()
            body = response.json()
            summary = body['message']['content']
        return MarketResult(correlation_id=task.correlation_id, status='completed', evidence=evidence,
            summary=summary, model=MODEL, measurements={
                'fixture_content_verified':1, 'source_sha256':source_digest, 'mcp_ms':round(mcp_ms, 3), 'mcp_tool_calls':1,
                'ollama_ms':round((perf_counter()-ollama_started)*1000, 3), 'ollama_calls':1,
                'prompt_tokens':body.get('prompt_eval_count', 0), 'output_tokens':body.get('eval_count', 0),
                'model_load_ms':round(body.get('load_duration', 0)/1e6, 3)}, limits=['Fonte interamente simulata; nessuna quotazione reale.', 'Sintesi generata dal modello e non verificata.', 'Nessun confronto economico personalizzato eseguito.'])
