"""Lo specialista richiede una sintesi al gateway, senza prompt o URL arbitrari."""
import httpx
from gateway.budgets import BUDGETS
from gateway import runtime
from gateway.identity import callback_headers
from gateway.a2a_egress import EgressDenied
from gateway.inference import InferenceResponse, MODELS

GATEWAY_ENDPOINT = 'http://127.0.0.1:8000/internal/inference'


async def request_summary(task, evidence):
    if not task.inference_token:
        raise EgressDenied('Autorizzazione inferenza assente')
    async with httpx.AsyncClient(timeout=BUDGETS.model_seconds+BUDGETS.transport_grace_seconds, trust_env=False, follow_redirects=False) as client:
        response = await client.post(runtime.GATEWAY_ENDPOINTS[task.scenario] + '/internal/inference' if runtime.ISOLATED else GATEWAY_ENDPOINT, json={
            'correlation_id': str(task.correlation_id), 'scenario': task.scenario,
            'evidence': evidence.model_dump(mode='json')},
            headers={**callback_headers(task.scenario), 'Authorization': 'Bearer ' + task.inference_token})
        if response.status_code == 403 or 300 <= response.status_code < 400:
            raise EgressDenied('Inferenza rifiutata dal gateway')
        if response.status_code == 504:
            raise TimeoutError('Timeout inferenza gateway')
        response.raise_for_status()
        result = InferenceResponse.model_validate(response.json())
        if result.model != MODELS[task.scenario]:
            raise ValueError('Modello difforme dalla configurazione')
        return result
