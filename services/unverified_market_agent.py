"""Fixture A2A negativa: dichiara completamento ma omette l'evidenza."""
from . import market_agent
from gateway.agent_contracts import MarketResult


async def missing_source(task):
    # Bypass intenzionale della validazione solo in questa fixture di protocollo.
    return MarketResult.model_construct(correlation_id=task.correlation_id,status='completed',evidence=None,
        summary='Conclusione non supportata da escludere.',limits=[],model='fixture-no-model',measurements={})


market_agent.perform=missing_source
app=market_agent.app
