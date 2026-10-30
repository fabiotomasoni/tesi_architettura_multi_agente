"""Dinieghi osservati prima del trasporto, senza servizi in ascolto."""
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import json
import httpx
import pytest
from a2a.client import A2AClient
from a2a.types import AgentCard, Message, MessageSendParams, Part, Role, SendMessageRequest, TextPart
from gateway.a2a_egress import A2AEgressTransport, EgressDenied, ROUTES
from gateway.agent_contracts import MarketTask, TaxTask


def task(scenario='S-01'):
    data = {'correlation_id':uuid4(), 'deadline':datetime.now(timezone.utc)+timedelta(seconds=60)}
    if scenario=='S-01':
        return MarketTask(**data, view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})
    return TaxTask(**data, view={'tax_year':2025,'purpose':'renovation'})


def envelope(t):
    return {'id':uuid4().hex,'jsonrpc':'2.0','method':'message/send','params':{'message':{'kind':'message','messageId':uuid4().hex,'parts':[{'kind':'text','text':t.model_dump_json()}],'role':'user'}}}


@pytest.mark.parametrize('scenario',['S-01','S-02'])
def test_real_sdk_through_egress(scenario):
    t=task(scenario); route=ROUTES[scenario]; sent=[]
    def receiver(req):
        sent.append(req)
        if req.method=='GET':return httpx.Response(200,json={})
        return httpx.Response(200,json={'jsonrpc':'2.0','id':json.loads(req.content)['id'],'result':{'kind':'message','messageId':uuid4().hex,'role':'agent','parts':[{'kind':'text','text':'ok'}]}})
    async def run():
        async with httpx.AsyncClient(transport=A2AEgressTransport(t,inner=httpx.MockTransport(receiver)),trust_env=False) as client:
            await client.get(route.endpoint+'.well-known/agent-card.json')
            card=AgentCard(name=route.agent_name,url=route.endpoint,version='0.1.0',description='test',capabilities={},skills=[],defaultInputModes=['text/plain'],defaultOutputModes=['text/plain'])
            sdk=A2AClient(httpx_client=client,agent_card=card)
            await sdk.send_message(SendMessageRequest(id=uuid4().hex,params=MessageSendParams(message=Message(message_id=uuid4().hex,role=Role.user,parts=[Part(root=TextPart(text=t.model_dump_json()))]))))
    asyncio.run(run())
    assert len(sent)==2
    assert json.loads(json.loads(sent[1].content)['params']['message']['parts'][0]['text'])==t.model_dump(mode='json')


@pytest.mark.parametrize('fault',['destination','query','method','header','metadata','payload','opaque','redirect','expired','policy'])
def test_denials(fault):
    t=task(); sent=[]; data=envelope(t); url=ROUTES['S-01'].endpoint; method='POST'; headers={}
    if fault=='destination':url='http://127.0.0.1:8002/'
    if fault=='query':url+='?name=secret'
    if fault=='method':method='PUT'
    if fault=='header':headers={'X-Secret':'secret'}
    if fault=='metadata':data['params']['metadata']={'secret':'value'}
    if fault=='payload':data['params']['message']['parts'][0]['text']=t.model_dump_json().replace('fixed','variable')
    if fault=='expired':t=t.model_copy(update={'deadline':datetime.now(timezone.utc)-timedelta(seconds=1)})
    if fault=='policy':t=t.model_copy(update={'policy_version':'0.1.0'})
    def receiver(req):
        sent.append(req)
        return httpx.Response(302,headers={'Location':'http://example.invalid/'})
    async def run():
        async with httpx.AsyncClient(transport=A2AEgressTransport(t,inner=httpx.MockTransport(receiver)),follow_redirects=True) as client:
            if fault=='opaque':await client.request(method,url,content=b'opaque')
            else:await client.request(method,url,json=data,headers=headers)
    with pytest.raises(EgressDenied):asyncio.run(run())
    assert len(sent)==(1 if fault=='redirect' else 0)


def test_workflow_denial_is_blocked_and_finalizes():
    from gateway.workflow import run_workflow
    cleared=[]
    async def denied(t):raise EgressDenied('Richiesta A2A fuori catalogo')
    result=asyncio.run(run_workflow(lambda:{'data':task().view.model_dump()},denied,lambda:cleared.append(True)))
    assert result['status']=='blocked'
    assert result['error_code']=='not_authorized'
    assert result['session_closed'] and cleared==[True]
    assert 'result' not in result
