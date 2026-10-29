"""Stessa API A2A, fixture MCP lenta e budget 2 s. Avviare al posto dell'agente normale."""
from . import market_agent
from .market_work import perform


async def timeout_work(task):
    return await perform(task, mcp_module='services.slow_rates_mcp', budget_seconds=2)


market_agent.perform = timeout_work
app = market_agent.app
