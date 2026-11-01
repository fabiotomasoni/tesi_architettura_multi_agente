"""Server MCP stdio: contesto tassi attraverso il gateway, fonte scelta dalla configurazione fidata."""
from mcp.server.fastmcp import FastMCP
from services.source_client import fetch_source

server = FastMCP('authorized_market_rates')


@server.tool()
def lookup_rates(mortgage_type: str | None = None, rate_type: str | None = None, remaining_years_band: dict | None = None, financial_profile: dict | None = None) -> dict:
    """Argomenti minimizzati o profilo finanziario del solo laboratorio, con controllo nel gateway."""
    if financial_profile is not None:
        if any(v is not None for v in (mortgage_type,rate_type,remaining_years_band,)):
            raise ValueError('Forme degli argomenti non combinabili')
        arguments={'financial_profile':financial_profile}
    else:arguments={'mortgage_type':mortgage_type,'rate_type':rate_type,'remaining_years_band':remaining_years_band}
    return fetch_source('lookup_rates',arguments)



if __name__ == '__main__':
    server.run(transport='stdio')
