"""Fixture avversaria: tenta di aggiungere un campo non ammesso alla fonte."""
from mcp.server.fastmcp import FastMCP
from services.source_client import fetch_source
server=FastMCP('forbidden_source_fixture')


@server.tool()
def lookup_rates(mortgage_type:str,rate_type:str,remaining_years_band:dict)->dict:
    return fetch_source('lookup_rates',{'mortgage_type':mortgage_type,'rate_type':rate_type,
        'remaining_years_band':remaining_years_band,'unauthorized_field':'synthetic-forbidden-value'})


if __name__=='__main__':server.run(transport='stdio')
