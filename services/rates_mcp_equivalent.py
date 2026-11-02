"""Implementazione MCP low-level equivalente: stesso tool e proxy, senza FastMCP."""
import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from services.source_client import fetch_source

server = Server('equivalent_market_rates', version='1.0.0')

# Contratto dichiarato esplicitamente, verificato contro quello dello standard.
SCHEMA = {
    'properties':{
        'mortgage_type':{'anyOf':[{'type':'string'},{'type':'null'}],'default':None,'title':'Mortgage Type'},
        'rate_type':{'anyOf':[{'type':'string'},{'type':'null'}],'default':None,'title':'Rate Type'},
        'remaining_years_band':{'anyOf':[{'additionalProperties':True,'type':'object'},{'type':'null'}],'default':None,'title':'Remaining Years Band'},
        'financial_profile':{'anyOf':[{'additionalProperties':True,'type':'object'},{'type':'null'}],'default':None,'title':'Financial Profile'},
    },
    'title':'lookup_ratesArguments','type':'object',
}


@server.list_tools()
async def list_tools():
    return [Tool(name='lookup_rates',description='Argomenti minimizzati o profilo finanziario del solo laboratorio, con controllo nel gateway.',inputSchema=SCHEMA)]


@server.call_tool()
async def call_tool(name, arguments):
    if name!='lookup_rates' or set(arguments)-set(SCHEMA['properties']):
        raise ValueError('Strumento o argomenti non supportati')
    if arguments.get('financial_profile') is not None:
        if any(arguments.get(k) is not None for k in ('mortgage_type','rate_type','remaining_years_band')):
            raise ValueError('Forme degli argomenti non combinabili')
        selected={'financial_profile':arguments['financial_profile']}
    else:
        selected={key:arguments.get(key) for key in ('mortgage_type','rate_type','remaining_years_band')}
    # La fonte e la ricevuta restano nel proxy: nessun dato inventato dal server.
    evidence=await asyncio.to_thread(fetch_source,'lookup_rates',selected)
    return [TextContent(type='text',text=json.dumps(evidence,ensure_ascii=False))]


async def main():
    async with stdio_server() as (incoming,outgoing):
        await server.run(incoming,outgoing,server.create_initialization_options())


if __name__=='__main__':asyncio.run(main())
