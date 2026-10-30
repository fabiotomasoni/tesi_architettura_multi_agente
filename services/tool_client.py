"""Client MCP dello specialista; l'autorità resta nel gateway."""
from gateway.a2a_egress import EgressDenied
from gateway.tool_egress import ToolPermit, TOOL_ROUTES
import httpx

GATEWAY_BASE = 'http://127.0.0.1:8000'


async def request_tool(task, *, mcp_module=None):
    if not task.inference_token:
        raise EgressDenied('Autorizzazione incarico assente')
    async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
        response = await client.post(GATEWAY_BASE + '/internal/tools/authorize',
            headers={'Authorization':'Bearer ' + task.inference_token}, json={
                'correlation_id':str(task.correlation_id), 'scenario':task.scenario,
                'tool':TOOL_ROUTES[task.scenario].tool, 'server_module':mcp_module, 'arguments':task.view.model_dump(mode='json')})
        if response.status_code == 403 or 300 <= response.status_code < 400:
            raise EgressDenied('Strumento rifiutato dal gateway')
        response.raise_for_status()
        return ToolPermit.model_validate(response.json())


def server_environment(task, permit):
    return {'TESI_SOURCE_TOKEN':permit.source_token, 'TESI_CORRELATION_ID':str(task.correlation_id),
            'TESI_SCENARIO':task.scenario, 'TESI_SOURCE_DESTINATION':permit.destination,
            'TESI_SOURCE_GATEWAY':GATEWAY_BASE + '/internal/sources'}
