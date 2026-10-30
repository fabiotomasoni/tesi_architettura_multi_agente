"""Lo specialista richiede una sintesi al gateway, senza prompt o URL arbitrari."""
import httpx
from gateway.a2a_egress import EgressDenied
from gateway.inference import InferenceResponse, MODELS

GATEWAY_ENDPOINT = 'http://127.0.0.1:8000/internal/inference'


async def request_summary(task, evidence):
    if not task.inference_token:
        raise EgressDenied('Autorizzazione inferenza assente')
    async with httpx.AsyncClient(timeout=95, trust_env=False, follow_redirects=False) as client:
        response = await client.post(GATEWAY_ENDPOINT, json={
            'correlation_id': str(task.correlation_id), 'scenario': task.scenario,
            'evidence': evidence.model_dump(mode='json')},
            headers={'Authorization': 'Bearer ' + task.inference_token})
        if response.status_code == 403 or 300 <= response.status_code < 400:
            raise EgressDenied('Inferenza rifiutata dal gateway')
        if response.status_code == 504:
            raise TimeoutError('Timeout inferenza gateway')
        response.raise_for_status()
        result = InferenceResponse.model_validate(response.json())
        if result.model != MODELS[task.scenario]:
            raise ValueError('Modello difforme dalla configurazione')
        return result
