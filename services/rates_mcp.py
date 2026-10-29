"""Server MCP stdio: fixture sintetica, nessuna fonte reale."""
from mcp.server.fastmcp import FastMCP
from gateway.agent_contracts import MarketView, RateEvidence

server = FastMCP('simulated_market_rates')


@server.tool()
def lookup_rates(mortgage_type: str, rate_type: str, remaining_years_band: dict) -> dict:
    """Restituisce un tasso simulato per verificare gli scambi del prototipo."""
    view = MarketView(mortgage_type=mortgage_type, rate_type=rate_type, remaining_years_band=remaining_years_band)
    rate = {'fixed':'3.20', 'variable':'3.60', 'mixed':'3.40'}[view.rate_type]
    return RateEvidence(annual_rate_percent=rate).model_dump(mode='json')


if __name__ == '__main__':
    server.run(transport='stdio')
