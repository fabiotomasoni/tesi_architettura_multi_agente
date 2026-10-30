"""Fixture fiscale: nessun riferimento di legge reale o calcolo di spettanza."""
from mcp.server.fastmcp import FastMCP
from services.source_client import fetch_source

server = FastMCP('simulated_tax')


@server.tool()
def lookup_tax(tax_year: int, expense_category: str, purpose: str) -> dict:
    """Restituisce condizioni inventate e marcate come simulate per test."""
    return fetch_source('lookup_tax', {'tax_year':tax_year,'expense_category':expense_category,'purpose':purpose})


if __name__=='__main__': server.run(transport='stdio')
