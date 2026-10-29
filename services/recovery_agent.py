"""Fixture recupero: prima richiesta MCP lenta, successive nominali nello stesso processo."""
from . import market_agent
from .market_work import perform
calls = 0


async def recovery_work(task):
    global calls
    calls += 1
    if calls == 1:
        return await perform(task, mcp_module='services.slow_rates_mcp', budget_seconds=2)
    return await perform(task)


market_agent.perform = recovery_work
app = market_agent.app
