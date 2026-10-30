"""Controlli negativi senza modelli né servizi reali."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import httpx
import pytest
from fastapi.testclient import TestClient
from gateway.app import create_app
from gateway.agent_contracts import MarketTask
import gateway.market_client as module


def task():
    return MarketTask(correlation_id=uuid4(), deadline=datetime.now(timezone.utc)+timedelta(seconds=60),view={'mortgage_type':'other','rate_type':'fixed','remaining_years_band':{'lower_exclusive':5,'upper_inclusive':10}})


@pytest.mark.parametrize('case', ['C006','C016'])
def test_incomplete_never_delegates(monkeypatch, case):
    async def forbidden(*args):
        pytest.fail('Delega effettuata con dati insufficienti')
    monkeypatch.setattr(module, 'delegate', forbidden)
    root=Path('dataset/Documents')
    with TestClient(create_app()) as c:
        r=c.post('/sessions/pdf', files=[('files',('mutuo.pdf',(root/f'{case}_mutuo.pdf').read_bytes()))], data={'scenarios':'S-01'})
        sid=r.json()['session_id']
        assert c.post(f'/sessions/{sid}/markets').status_code==409
        assert c.delete(f'/sessions/{sid}').status_code==204


@pytest.mark.parametrize('fault', ['card','source','correlation'])
def test_card_and_result_rejection(monkeypatch, fault):
    request=task()
    card={'name':'markets_agent','url':module.ENDPOINT,'version':'0.1.0','description':'test','capabilities':{'streaming':False},'skills':[{'id':'market_rate_context','name':'rates','description':'test','tags':[]}],'defaultInputModes':['text/plain'],'defaultOutputModes':['text/plain']}
    if fault=='card':card['url']='http://127.0.0.1:9999/'
    sent=[]
    class FakeHTTP:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url):return httpx.Response(200,json=card,request=httpx.Request('GET',url))
    class FakeA2A:
        def __init__(self,**kwargs):pass
        async def send_message(self,message):
            sent.append(message)
            result={'correlation_id':str(uuid4() if fault=='correlation' else request.correlation_id),'status':'completed','evidence':None if fault=='source' else {'annual_rate_percent':'3.20'},'summary':'test','limits':[],'model':'test'}
            return SimpleNamespace(model_dump=lambda **kw:{'result':{'parts':[{'kind':'text','text':json.dumps(result)}]}})
    monkeypatch.setattr(module.httpx,'AsyncClient',FakeHTTP)
    monkeypatch.setattr(module,'A2AClient',FakeA2A)
    if fault=='source':
        parsed=asyncio.run(module.delegate(request))
        assert parsed.status=='unverified' and parsed.error_code=='missing_provenance'
    else:
        with pytest.raises(ValueError):asyncio.run(module.delegate(request))
    if fault=='card':assert not sent


def test_ollama_payload_contains_only_simulated_evidence(monkeypatch):
    import services.market_work as work
    captured=[]
    class FakeHTTP:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,json):
            captured.append(json)
            return httpx.Response(200,json={'message':{'content':'Dati simulati'},'prompt_eval_count':10,'eval_count':3},request=httpx.Request('POST',url))
    monkeypatch.setattr(work.httpx,'AsyncClient',FakeHTTP)
    result=asyncio.run(work.perform(task()))  # MCP stdio reale, Ollama sostituito.
    assert result.status=='completed'
    payload=captured[0]
    assert json.loads(payload['messages'][1]['content'])==result.evidence.model_dump(mode='json')
    assert result.measurements['mcp_tool_calls']==1
    assert result.measurements['output_tokens']==3
