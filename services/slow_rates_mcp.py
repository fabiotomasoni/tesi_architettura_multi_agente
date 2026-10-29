"""Fixture negativa separata: attesa artificiale, mai selezionata dalla demo normale."""
import asyncio
from mcp.server.fastmcp import FastMCP
server = FastMCP('slow_rates_fixture')


@server.tool()
async def lookup_rates(mortgage_type: str, rate_type: str, remaining_years_band: dict) -> dict:
    """Attende 10 s per superare il budget della fixture timeout (2 s)."""
    await asyncio.sleep(10)
    return {'annual_rate_percent':'3.20'}


if __name__ == '__main__':
    server.run(transport='stdio')
