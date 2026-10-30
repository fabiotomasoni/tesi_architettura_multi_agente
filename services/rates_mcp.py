"""Server MCP stdio: fixture sintetica, nessuna fonte reale."""
from mcp.server.fastmcp import FastMCP
from services.source_client import fetch_source

server = FastMCP('simulated_market_rates')


@server.tool()
def lookup_rates(mortgage_type: str, rate_type: str, remaining_years_band: dict) -> dict:
    """Restituisce un tasso simulato per verificare gli scambi del prototipo."""
    return fetch_source('lookup_rates', {'mortgage_type':mortgage_type,'rate_type':rate_type,'remaining_years_band':remaining_years_band})


if __name__ == '__main__':
    server.run(transport='stdio')
