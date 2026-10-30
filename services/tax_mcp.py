"""Fixture fiscale: nessun riferimento di legge reale o calcolo di spettanza."""
from mcp.server.fastmcp import FastMCP
from gateway.agent_contracts import TaxView
from gateway.tax_evidence import expected_evidence
server = FastMCP('simulated_tax')


@server.tool()
def lookup_tax(tax_year: int, expense_category: str, purpose: str) -> dict:
    """Restituisce condizioni inventate e marcate come simulate per test."""
    view=TaxView(tax_year=tax_year,expense_category=expense_category,purpose=purpose)
    return expected_evidence(view).model_dump(mode='json')


if __name__=='__main__': server.run(transport='stdio')
