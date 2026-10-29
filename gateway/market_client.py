"""Adattatore gateway: verifica Card e delega solo all'endpoint locale fissato."""
from uuid import uuid4
from time import perf_counter
import httpx
from a2a.client import A2AClient
from a2a.types import AgentCard, SendMessageRequest, MessageSendParams, Message, Role, Part, TextPart
from .agent_contracts import MarketTask, MarketResult

ENDPOINT = 'http://127.0.0.1:8001/'


async def delegate(task: MarketTask) -> MarketResult:
    async with httpx.AsyncClient(timeout=125, trust_env=False, follow_redirects=False) as client:
        started = perf_counter()
        response = await client.get(ENDPOINT + '.well-known/agent-card.json')
        response.raise_for_status()
        card = AgentCard.model_validate(response.json())
        if card.name != 'markets_agent' or card.url != ENDPOINT or card.version != '0.1.0' or {s.id for s in card.skills} != {'market_rate_context'} or card.capabilities.streaming:
            raise ValueError('Agent Card difforme dalla configurazione autorizzata')
        card_ms = (perf_counter()-started)*1000
        started = perf_counter()
        remote = A2AClient(httpx_client=client, agent_card=card)
        reply = await remote.send_message(SendMessageRequest(id=uuid4().hex, params=MessageSendParams(
            message=Message(message_id=uuid4().hex, role=Role.user, parts=[Part(root=TextPart(text=task.model_dump_json()))]))))
        data = reply.model_dump(mode='json', by_alias=True)
        result = data.get('result', {})
        parts = result.get('parts', [])
        for artifact in result.get('artifacts', []):
            parts.extend(artifact.get('parts', []))
        for part in parts:
            if part.get('kind') == 'text':
                parsed = MarketResult.model_validate_json(part['text'])
                if parsed.correlation_id != task.correlation_id:
                    raise ValueError('Correlazione del risultato non valida')
                parsed.measurements.update({'card_validation_ms':round(card_ms, 3), 'a2a_roundtrip_ms':round((perf_counter()-started)*1000, 3), 'a2a_requests':1, 'card_validated':1, 'result_validated':1})
                return parsed
        raise ValueError('Risultato A2A privo di artefatto strutturato')
