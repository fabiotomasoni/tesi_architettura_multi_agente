"""Fixture MCP negativa: dati strutturati ma source_id intenzionalmente omesso."""
from mcp.server.fastmcp import FastMCP
from gateway.agent_contracts import MarketView,TaxView
from gateway.market_evidence import expected_evidence as market
from gateway.tax_evidence import expected_evidence as tax
server=FastMCP('missing_source_fixture')


@server.tool()
def lookup_rates(mortgage_type:str,rate_type:str,remaining_years_band:dict)->dict:
    evidence=market(MarketView(mortgage_type=mortgage_type,rate_type=rate_type,remaining_years_band=remaining_years_band)).model_dump(mode='json')
    evidence.pop('source_id')
    return evidence


@server.tool()
def lookup_tax(tax_year:int,expense_category:str,purpose:str)->dict:
    evidence=tax(TaxView(tax_year=tax_year,expense_category=expense_category,purpose=purpose)).model_dump(mode='json')
    evidence.pop('source_id')
    return evidence


if __name__=='__main__':server.run(transport='stdio')
