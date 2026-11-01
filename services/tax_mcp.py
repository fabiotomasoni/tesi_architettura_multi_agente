"""Fonte fiscale autorizzata dal gateway; nessun calcolo di spettanza."""
from mcp.server.fastmcp import FastMCP
from services.source_client import fetch_source

server = FastMCP('authorized_tax')


@server.tool()
def lookup_tax(tax_year: int | None = None, expense_category: str | None = None, purpose: str | None = None, financial_profile: dict | None = None) -> dict:
    """Argomenti minimizzati o profilo finanziario del solo laboratorio, con controllo nel gateway."""
    if financial_profile is not None:
        if any(v is not None for v in (tax_year,expense_category,purpose,)):
            raise ValueError('Forme degli argomenti non combinabili')
        arguments={'financial_profile':financial_profile}
    else:arguments={'tax_year':tax_year,'expense_category':expense_category,'purpose':purpose}
    return fetch_source('lookup_tax',arguments)



if __name__=='__main__': server.run(transport='stdio')
