"""Client di verifica del tool malevolo: MCP stdio reale, nessun incarico finanziario."""
import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(role):
    parameters=StdioServerParameters(command=sys.executable,args=['-m','services.network_probe_mcp'],env={'TESI_PROBE_ROLE':role})
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize()
            result=await client.call_tool('attempt_direct_connections',{})
            if result.isError:raise RuntimeError('Probe MCP fallito')
            data=json.loads(result.content[0].text)
    print(json.dumps(data),flush=True)


if __name__=='__main__':
    asyncio.run(main(sys.argv[1]))
