"""Server MCP stdio: contesto tassi attraverso il gateway, fonte scelta dalla configurazione fidata."""
from mcp.server.fastmcp import FastMCP
from services.source_client import fetch_source

server = FastMCP('authorized_market_rates')


@server.tool()
def lookup_rates(mortgage_type: str, rate_type: str, remaining_years_band: dict) -> dict:
    """Richiede un riferimento sui tassi alla fonte autorizzata dal gateway."""
    return fetch_source('lookup_rates', {'mortgage_type':mortgage_type,'rate_type':rate_type,'remaining_years_band':remaining_years_band})


if __name__ == '__main__':
    server.run(transport='stdio')
