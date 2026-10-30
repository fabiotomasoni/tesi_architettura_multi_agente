"""Server MCP stdio: fixture sintetica, nessuna fonte reale."""
from mcp.server.fastmcp import FastMCP
from gateway.agent_contracts import MarketView
from gateway.market_evidence import expected_evidence

server = FastMCP('simulated_market_rates')


@server.tool()
def lookup_rates(mortgage_type: str, rate_type: str, remaining_years_band: dict) -> dict:
    """Restituisce un tasso simulato per verificare gli scambi del prototipo."""
    view = MarketView(mortgage_type=mortgage_type, rate_type=rate_type, remaining_years_band=remaining_years_band)
    return expected_evidence(view).model_dump(mode='json')


if __name__ == '__main__':
    server.run(transport='stdio')
