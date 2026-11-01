"""Una sola delega A2A al generalista, con capability distinte per attività."""
import asyncio,json
from time import perf_counter
from uuid import uuid4
import httpx
from a2a.client import A2AClient
from a2a.types import AgentCard,SendMessageRequest,MessageSendParams,Message,Role,Part,TextPart
from .agent_contracts import BatchTask,MarketResult,MarketEvidence,TaxResult
from .a2a_egress import A2AEgressTransport,ROUTES
from .market_evidence import verify_evidence as markets,provenance_fields as market_fields
from .tax_evidence import verify_evidence as tax,TaxEvidenceParser,provenance_fields as tax_fields
from .result_validation import parse_result
from .inference import MODELS


class BatchDelegate:
    def __init__(self,expected):
        self.expected=tuple(expected);self.tasks={};self.waiters={}
        self.measurements={'a2a_delegations_attempted':0,'a2a_message_sends':0}

    async def submit(self,task):
        if task.scenario not in self.expected or task.scenario in self.tasks:raise ValueError('Attività aggregata inattesa')
        self.tasks[task.scenario]=task
        future=asyncio.get_running_loop().create_future();self.waiters[task.scenario]=future
        if len(self.tasks)==len(self.expected):
            try:
                results=await self.send([self.tasks[s] for s in self.expected])
                for s,f in self.waiters.items():
                    if not f.done():f.set_result(results[s])
            except BaseException as error:
                for f in self.waiters.values():
                    if not f.done():
                        if isinstance(error,asyncio.CancelledError):f.cancel()
                        else:f.set_exception(error)
                if isinstance(error,asyncio.CancelledError):raise
        return await future

    async def send(self,tasks):
        batch=BatchTask(correlation_id=uuid4(),deadline=min(t.deadline for t in tasks),tasks=tasks)
        self.measurements['a2a_delegations_attempted']+=1
        route=ROUTES['BATCH'];began=perf_counter()
        transport=A2AEgressTransport(batch)
        async with httpx.AsyncClient(timeout=125,trust_env=False,follow_redirects=False,transport=transport) as client:
            response=await client.get(route.endpoint+'.well-known/agent-card.json');response.raise_for_status()
            card=AgentCard.model_validate(response.json())
            if card.name!=route.agent_name or card.url!=route.endpoint or card.version!='0.1.0' or {s.id for s in card.skills}!={route.skill} or card.capabilities.streaming:
                raise ValueError('Card generalista difforme')
            self.measurements['card_validation_ms']=round((perf_counter()-began)*1000,3)
            started=perf_counter();sdk=A2AClient(httpx_client=client,agent_card=card)
            try:
                reply=await sdk.send_message(SendMessageRequest(id=uuid4().hex,params=MessageSendParams(message=Message(message_id=uuid4().hex,role=Role.user,parts=[Part(root=TextPart(text=batch.model_dump_json()))]))))
            finally:
                self.measurements['a2a_message_sends']=transport.message_sends
            self.measurements['a2a_roundtrip_ms']=round((perf_counter()-started)*1000,3)
            data=reply.model_dump(mode='json',by_alias=True).get('result',{})
            parts=list(data.get('parts',[]))
            for a in data.get('artifacts',[]):parts.extend(a.get('parts',[]))
            texts=[p['text'] for p in parts if p.get('kind')=='text']
            if len(texts)!=1:raise ValueError('Artefatto aggregato mancante o duplicato')
            return parse_batch(texts[0],batch)


def parse_batch(text,batch):
    raw=json.loads(text)
    if set(raw)!={'correlation_id','results'} or raw['correlation_id']!=str(batch.correlation_id) or set(raw['results'])!={t.scenario for t in batch.tasks}:
        raise ValueError('Risultato aggregato incoerente')
    results={}
    for task in batch.tasks:
        s=task.scenario;item=raw['results'][s]
        result=parse_result(json.dumps(item),task,MarketResult if s=='S-01' else TaxResult,MarketEvidence if s=='S-01' else TaxEvidenceParser,(market_fields if s=='S-01' else tax_fields)(item.get('evidence')))
        if result.model!=MODELS[s]:raise ValueError('Modello sperimentale difforme')
        if result.evidence is not None:
            _,digest=(markets if s=='S-01' else tax)(result.evidence,task.view)
            result.measurements.update(source_sha256=digest,source_content_verified=1,fixture_content_verified=1)
        # Il solo coordinatore conta la delega comune, non ciascun risultato.
        result.measurements.update(a2a_requests=0,card_validated=1,result_validated=1,provenance_verified=int(result.status=='completed'))
        results[s]=result
    return results
