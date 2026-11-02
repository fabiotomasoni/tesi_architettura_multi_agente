"""Consultazione MCP pubblica senza attributi del fascicolo."""
from mcp.server.fastmcp import FastMCP
from services.source_client import fetch_source
server=FastMCP('authorized_common_reference')
@server.tool()
def lookup_reference() -> dict:
    """Legge il riferimento comune fissato dal gateway, senza dati personali."""
    return fetch_source('lookup_reference',{})
if __name__=='__main__':server.run(transport='stdio')
