"""Permesso monouso distinto per la consultazione comune di ciascun agente."""
from copy import deepcopy
from secrets import token_hex
from . import verification_config as config
from .a2a_egress import EgressDenied,authorized_task
from .shared_reference import DESTINATION,MODULE,TOOL,expected

def authorize(broker,request,authorization,permit_type):
    token=authorization[7:] if authorization and authorization.startswith('Bearer ') else None
    with broker._lock:
        grant=broker._grants.get(token)
        if not config.SHARED or grant is None or grant.reference_token is not None:raise EgressDenied('Riferimento non autorizzato')
        _,task=authorized_task(grant.task)
        if (request.scenario!=task.scenario or request.correlation_id!=task.correlation_id or request.tool!=TOOL
            or request.arguments!={} or request.server_module not in (None,MODULE)):
            raise EgressDenied('Richiesta del riferimento difforme')
        grant.reference_token=token_hex(32)
        return permit_type(module=MODULE,tool=TOOL,destination=DESTINATION,source_token=grant.reference_token,arguments={})

async def read(broker,request,authorization):
    token=authorization[7:] if authorization and authorization.startswith('Bearer ') else None
    with broker._lock:
        grant=next((g for g in broker._grants.values() if g.reference_token and g.reference_token==token),None)
        if not config.SHARED or grant is None or grant.reference_used:raise EgressDenied('Fonte comune non autorizzata')
        _,task=authorized_task(grant.task)
        if (request.scenario!=task.scenario or request.correlation_id!=task.correlation_id or request.tool!=TOOL
            or request.arguments!={} or request.destination!=DESTINATION or request.headers!={}
            or request.method!='POST' or request.server_module is not None):raise EgressDenied('Fonte comune difforme')
        grant.reference_used=True
        data=expected(task.scenario,config.PROFILE).model_dump(mode='json')
        grant.reference_evidence=deepcopy(data)
        return data
