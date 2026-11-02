"""Lettura comune degli agenti: MCP reale e proxy con capability separata."""
import json,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from gateway import verification_config as config
from gateway.shared_reference import TOOL,verify
from gateway.a2a_egress import EgressDenied
from services.tool_client import request_reference,server_environment
from services.mcp_contract import check_tools
from services.work_metrics import count
async def read_reference(task):
    if not config.SHARED:return None
    permit=await request_reference(task)
    parameters=StdioServerParameters(command=sys.executable,args=['-m',permit.module],env=server_environment(task,permit))
    count('mcp_sessions_started')
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize();await check_tools(client,TOOL)
            count('mcp_tool_calls')
            result=await client.call_tool(permit.tool,permit.arguments)
            count('mcp_tool_calls_completed')
            if result.isError:raise ValueError('Errore MCP riferimento comune')
            raw=json.loads(result.content[0].text)
    receipt,_=verify(raw,task.scenario)
    if config.PROFILE=='unfaithful_result' and task.scenario=='S-01':
        receipt=receipt.model_copy(update={'value':'99.00'})
    return receipt.model_dump(mode='json')
