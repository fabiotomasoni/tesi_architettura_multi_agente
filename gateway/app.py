"""API locale: avviare con un solo worker; inferenza locale tramite broker autorizzato."""
from contextlib import asynccontextmanager, suppress
import asyncio
from copy import deepcopy
from threading import RLock
from time import monotonic, perf_counter
from uuid import UUID, uuid4

import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse

from . import runtime
from .identity import HEADER, load_identity, matching_key, SCENARIO_ROLES
from .ollama_bridge import OllamaBridge
from .privacy import SensitiveContext, PRIVACY_VERSION, ENTITY_RECOGNIZER_VERSION
from .inference import InferenceBroker, InferenceRequest
from .tool_egress import ToolRequest, SourceRequest, authorize_tool, source_request, MARKET_SOURCE, TAX_SOURCE, MARKET_TOOL_IMPLEMENTATION, TOOL_CATALOG_VERSION
from .a2a_egress import EgressDenied
from .models import SessionInput, ViewRequest, Scenario
from .pdf_input import extract_profile, PDFInputError
from .policy import POLICY_VERSION, issues, make_view
from .tracing import TraceStore, TraceMiddleware, Span, measured, trace_id, context, use_trace, request_outcome, TRACE_VERSION
from .budgets import BUDGETS

SESSION_TTL_SECONDS = 1800
SESSION_SWEEP_SECONDS = 30
CANCELLATION_GRACE_SECONDS = 5


def create_app() -> FastAPI:
    if runtime.EXPERIMENT!='off' and not runtime.ISOLATED:
        raise RuntimeError('La sperimentazione richiede i container isolati')
    sessions = {}
    gateway_boot_id = uuid4().hex
    traces = TraceStore(gateway_boot_id)
    broker = InferenceBroker()
    broker.require_session = True
    if runtime.ISOLATED:
        if load_identity()['role'] != 'gateway':
            raise RuntimeError('Identità gateway obbligatoria')
        broker.bridge = OllamaBridge()
    lock = RLock()
    active = {}

    def finish_session(session_id):
        selected = context() or traces.for_session(session_id, include_closed=True)
        with use_trace(selected), Span('cleanup') as observation:
            with lock:
                observation.metric(sessions_removed=int(session_id in sessions))
                sessions.pop(session_id, None)
                broker.revoke(session_id)
                traces.closed(session_id)

    def stop_session(session_id, reason):
        with lock:
            finish_session(session_id)
            operation = active.get(session_id)
            if operation is not None and operation['reason'] is None:
                operation['reason'] = reason
                task = operation['task']
                # Anche il controllo TTL può arrivare da un endpoint sincrono.
                task.get_loop().call_soon_threadsafe(task.cancel)
            return operation

    async def run_operation(session_id, request, execute, *, close_on_finish=True):
        with lock:
            get_session(session_id)
            if session_id in active:
                raise HTTPException(409, {'error_code':'analysis_already_running', 'message':'Un’attività è già in corso per questa sessione.'})
            operation = {'task':asyncio.create_task(execute()), 'reason':None}
            active[session_id] = operation

        async def disconnected():
            try:
                while True:
                    message = await request.receive()
                    if message['type'] == 'http.disconnect':
                        break
            except Exception:
                pass  # Errore del canale di ingresso: il lavoro non resta orfano.
            stop_session(session_id, 'client_disconnected')

        watcher = asyncio.create_task(disconnected())
        def cancelled_response():
            request_outcome('cancelled')
            return JSONResponse(status_code=409, content={
                'status':'cancelled', 'error_code':'analysis_cancelled',
                'session_closed':True, 'reason':operation['reason'],
                'message':'Analisi annullata; nessun report consegnato.'})
        try:
            result = await operation['task']
            return cancelled_response() if operation['reason'] is not None else result
        except asyncio.CancelledError:
            if operation['reason'] is None:
                stop_session(session_id, 'request_cancelled')
                raise
            return cancelled_response()
        except Exception:
            if operation['reason'] is not None:
                return cancelled_response()
            raise
        finally:
            watcher.cancel()
            with suppress(asyncio.CancelledError):
                await watcher
            with lock:
                if close_on_finish or operation['reason'] is not None:
                    finish_session(session_id)
                if active.get(session_id) is operation:
                    active.pop(session_id)

    def expire_sessions():
        with lock:
            for key in [key for key, (_, deadline) in sessions.items() if deadline <= monotonic()]:
                stop_session(key, 'session_expired')

    async def sweep_sessions():
        while True:
            await asyncio.sleep(SESSION_SWEEP_SECONDS)
            expire_sessions()

    @asynccontextmanager
    async def lifespan(app):
        sweeper = asyncio.create_task(sweep_sessions())
        try:
            yield
        finally:
            sweeper.cancel()
            with suppress(asyncio.CancelledError):
                await sweeper
            pending = []
            with lock:
                for sid in list(active):
                    operation = stop_session(sid, 'shutdown')
                    if operation is not None:
                        pending.append(operation['task'])
            if pending:
                await asyncio.wait(pending, timeout=CANCELLATION_GRACE_SECONDS)
            with lock:
                sessions.clear()
                broker.revoke()
                if broker.bridge is not None:
                    broker.bridge.close()

    app = FastAPI(title="Gateway locale sperimentale", version="0.1.0", lifespan=lifespan)
    app.add_middleware(TraceMiddleware, store=traces)

    @app.get('/traces/{identifier}')
    def read_trace(identifier: UUID):
        result = traces.snapshot(identifier)
        if result is None:
            raise HTTPException(404, 'Traccia assente, scaduta o persa dopo il riavvio.')
        return result

    @app.middleware('http')
    async def verify_workload_identity(request: Request, call_next):
        if runtime.ISOLATED:
            path = request.url.path
            peer = request.client.host if request.client else ''
            values = request.headers.getlist(HEADER)
            received = values[0] if len(values) == 1 else None
            if path.startswith('/internal/'):
                principal = next((role for role in set(SCENARIO_ROLES.values())
                                  if matching_key(received, role + '_to_gateway')), None)
                if principal is None or (peer in runtime.PEER_SCENARIOS and SCENARIO_ROLES[runtime.PEER_SCENARIOS[peer]]!=principal):
                    return JSONResponse(status_code=403, content={'detail':'Identità del chiamante non autorizzata.'})
                request.state.principal = principal
            elif path.startswith('/_bridge/'):
                if peer in runtime.PEER_SCENARIOS or not matching_key(received, 'bridge'):
                    return JSONResponse(status_code=403, content={'detail':'Ponte non autorizzato.'})
            elif peer in runtime.PEER_SCENARIOS or received is not None:
                return JSONResponse(status_code=403, content={'detail':'Percorso non autorizzato al componente.'})
        return await call_next(request)

    def verify_scenario(request, scenario):
        if runtime.ISOLATED and request.state.principal != SCENARIO_ROLES[scenario]:
            raise EgressDenied('Scenario non autorizzato al chiamante')

    @app.get('/_bridge/poll', include_in_schema=False)
    async def bridge_poll():
        if broker.bridge is None:
            raise HTTPException(404, 'Ponte non attivo.')
        job = await broker.bridge.poll()
        return JSONResponse(job) if job else Response(status_code=204)

    @app.get('/_bridge/status/{job_id}', include_in_schema=False)
    async def bridge_status(job_id: str):
        if broker.bridge is None:
            raise HTTPException(404, 'Ponte non attivo.')
        if not broker.bridge.is_active(job_id):
            raise HTTPException(409, 'Incarico del ponte assente o terminato.')
        return Response(status_code=204)

    @app.post('/_bridge/result/{job_id}', include_in_schema=False)
    async def bridge_result(job_id: str, request: Request):
        if broker.bridge is None:
            raise HTTPException(404, 'Ponte non attivo.')
        # Limite sulla lettura effettiva, anche senza Content-Length.
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 65536:
                raise HTTPException(413, 'Risultato del ponte troppo grande.')
        try:
            import json
            result = json.loads(data)
            base = set(result)-{'execution'}
            if base not in ({'body','error','ollama_ms'}, {'body','error','ollama_ms','source_ms'}) or result['error'] not in (None,'timeout','unavailable'):
                raise ValueError()
            if (result['body'] is None) == (result['error'] is None):
                raise ValueError()
            import math
            kind=broker.bridge.kind(job_id)
            if kind is None:
                return JSONResponse(status_code=409,content={'detail':'Incarico del ponte assente o terminato.'})
            from .http_observation import validate_execution
            validate_execution(result.get('execution'),kind)
            field='source_ms' if kind in {'ecb_market_source','ade_tax_source'} else 'ollama_ms'
            ms=result.get(field)
            if result['error'] is None and (type(ms) not in (int,float) or not math.isfinite(ms) or ms < 0):
                raise ValueError()
            other='ollama_ms' if field=='source_ms' else 'source_ms'
            if result.get(other) is not None or (result['error'] is not None and ms is not None):
                raise ValueError()
            accepted = broker.bridge.complete(job_id, **result)
        except Exception:
            raise HTTPException(422, 'Risultato del ponte non conforme.') from None
        if not accepted:
            raise HTTPException(409, 'Incarico del ponte assente o terminato.')
        return {'accepted': True}

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Non riflettere nel messaggio i valori o il corpo della richiesta.
        return JSONResponse(status_code=422, content={"detail": "Ingresso non conforme allo schema; controllare campi, tipi e categorie."})

    def get_session(session_id):
        expire_sessions()
        if session_id not in sessions:
            raise HTTPException(404, "Sessione assente o scaduta")
        return sessions[session_id][0]

    @app.post("/internal/inference")
    async def inference(payload: InferenceRequest, request: Request):
        try:
            verify_scenario(request, payload.scenario)
            return await broker.infer(payload, request.headers.get('authorization'))
        except EgressDenied:
            raise HTTPException(403, "Inferenza non autorizzata dal gateway.") from None
        except (TimeoutError, httpx.TimeoutException):
            raise HTTPException(504, "Tempo massimo inferenza superato.") from None
        except Exception:
            raise HTTPException(502, "Inferenza locale non completata.") from None

    @app.post("/internal/tools/authorize")
    async def tool_authorization(payload: ToolRequest, request: Request):
        try:
            verify_scenario(request, payload.scenario)
            return authorize_tool(broker, payload, request.headers.get('authorization'))
        except EgressDenied:
            raise HTTPException(403, "Strumento non autorizzato dal gateway.") from None

    @app.post("/internal/sources")
    async def source_proxy(payload: SourceRequest, request: Request):
        try:
            verify_scenario(request, payload.scenario)
            return await source_request(broker, payload, request.headers.get('authorization'))
        except EgressDenied:
            raise HTTPException(403, "Fonte non autorizzata dal gateway.") from None
        except (TimeoutError, httpx.TimeoutException):
            raise HTTPException(504, "Tempo massimo fonte superato.") from None
        except Exception:
            raise HTTPException(502, "Fonte non disponibile.") from None

    @app.get("/health")
    def health():
        return {"status": "ok", "policy_version": POLICY_VERSION,
                "gateway_boot_id": gateway_boot_id,
                "trace_version": TRACE_VERSION, "budgets": BUDGETS.public(),
                "market_tool_implementation": MARKET_TOOL_IMPLEMENTATION, "tool_catalog_version": TOOL_CATALOG_VERSION,
                "runtime_mode": runtime.MODE, "experiment": runtime.EXPERIMENT, "minimization": runtime.MINIMIZATION, "market_source": MARKET_SOURCE, "tax_source": TAX_SOURCE, "identity_version": runtime.IDENTITY_VERSION,
                "privacy_version": PRIVACY_VERSION, "entity_recognizer_version": ENTITY_RECOGNIZER_VERSION}

    @app.post("/sessions", status_code=201)
    def create_session(payload: SessionInput):
        if runtime.EXPERIMENT!='off':raise HTTPException(403,'Nel laboratorio usare solo i PDF del corpus sintetico fissato.')
        with Span('privacy_context'):
            context = SensitiveContext.from_profile(payload.profile)
        return register_session(payload, context)

    def register_session(payload, context):
        with lock:
            expire_sessions()
            sid = uuid4()
            broker._privacy[sid]=context
            if runtime.UNMINIMIZED:
                from .lab_profile import full_view
                broker._lab_profiles[sid]=full_view(payload.profile)
            sessions[sid] = (deepcopy(payload), monotonic() + SESSION_TTL_SECONDS)
            traces.bind_session(sid)
            with Span('profile_validation'):
                readiness = {s.value: {"ready": not issues(payload.profile, s), "issues": issues(payload.profile, s)} for s in set(payload.scenarios)}
            return {"session_id": str(sid), "trace_id": trace_id(), "policy_version": POLICY_VERSION,
                    "scenarios": readiness}

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.post("/sessions/pdf", status_code=201)
    async def upload_pdf(files: list[UploadFile] = File(...), scenarios: list[Scenario] = Form(...)):
        try:
            if not 1 <= len(files) <= 4:
                raise HTTPException(400, "Caricare da uno a quattro PDF dello stesso fascicolo.")
            contents = []
            lab_cases=set()
            rejected_documents = []
            for index, file in enumerate(files, 1):
                with Span('input_read'):
                    content = await file.read(5 * 1024 * 1024 + 1)
                if len(content) > 5 * 1024 * 1024:
                    raise HTTPException(413, "Ogni PDF deve essere inferiore a 5 MiB.")
                if runtime.EXPERIMENT!='off':
                    import hashlib
                    from .lab_corpus import PDF_CASES
                    case=PDF_CASES.get(hashlib.sha256(content).hexdigest())
                    if case is None:raise HTTPException(403,'PDF fuori dal corpus sintetico autorizzato per il laboratorio.')
                    lab_cases.add(case)
                    if len(lab_cases)>1:raise HTTPException(400,'Nel laboratorio caricare un solo fascicolo per sessione.')
                try:
                    # Prevalidazione separata: un file rifiutato non entra nell'aggregazione.
                    with Span('pdf_prevalidation'):
                        extract_profile([content])
                except PDFInputError as exc:
                    rejected_documents.append({'upload_index': index, 'reason': str(exc)})
                    continue
                contents.append(content)
            if not contents:
                raise HTTPException(400, {'message': 'Nessun PDF utilizzabile.', 'rejected_documents': rejected_documents})
            try:
                with Span('extraction') as extraction:
                    profile, documents = extract_profile(contents)
                    extraction.metric(documents=len(documents), rejected_documents=len(rejected_documents))
            except PDFInputError as exc:
                raise HTTPException(400, str(exc)) from None
            try:
                with Span('privacy_context'):
                    context = SensitiveContext.from_profile(profile)
                    context.add_documents(contents)
            except Exception:
                raise HTTPException(400, 'Impossibile completare il controllo privacy locale dei PDF.') from None
            result = register_session(SessionInput(scenarios=scenarios, profile=profile), context)
            return {**result, "documents": documents, "rejected_documents": rejected_documents, "profile": profile.model_dump(mode="json")}
        finally:
            for file in files:
                await file.close()

    @app.post("/sessions/{session_id}/views")
    @measured('policy_view', scenario_parameter='request')
    def view(session_id: UUID, request: ViewRequest):
        with lock:
            session = get_session(session_id)
            expected = "markets" if request.scenario == Scenario.MORTGAGE else "tax"
            if request.scenario not in session.scenarios or request.recipient != expected:
                raise HTTPException(403, "Attività o destinatario non autorizzato")
            problems = issues(session.profile, request.scenario)
            if problems:
                raise HTTPException(409, {"message": "Dati insufficienti per l'attività", "issues": problems})
            return {"scenario": request.scenario, "recipient": request.recipient,
                    "policy_version": POLICY_VERSION, "data": make_view(session.profile, request.scenario)}

    @app.post("/sessions/{session_id}/markets")
    async def run_markets(session_id: UUID, request: Request):
        return await run_operation(session_id, request, lambda: execute_markets(session_id), close_on_finish=False)

    async def execute_markets(session_id):
        if runtime.EXPERIMENT!='off':raise HTTPException(409,'Nel laboratorio usare il percorso analysis con budget di sessione comune.')
        from datetime import datetime, timedelta, timezone
        from .agent_contracts import MarketTask, MarketView
        from .market_client import delegate
        from .a2a_egress import EgressDenied
        started = perf_counter()
        permitted = view(session_id, ViewRequest(scenario=Scenario.MORTGAGE, recipient="markets"))
        view_ms = (perf_counter()-started)*1000
        task = MarketTask(correlation_id=uuid4(), deadline=datetime.now(timezone.utc) + timedelta(seconds=BUDGETS.activity_seconds),
                          view=MarketView.model_validate(permitted["data"]))
        try:
            result = await broker.delegate(session_id, task, delegate)
        except EgressDenied:
            raise HTTPException(403, "Richiesta A2A bloccata dal catalogo delle uscite.") from None
        except Exception:
            raise HTTPException(502, "Delega non completata: controllare servizio mercati, Card e Ollama.") from None
        result.measurements.update({'view_ms':round(view_ms, 3), 'gateway_total_ms':round((perf_counter()-started)*1000, 3)})
        return result.model_dump(mode="json")

    @app.post("/sessions/{session_id}/workflow")
    async def workflow(session_id: UUID, request: Request):
        if runtime.EXPERIMENT!='off':raise HTTPException(409,'Nel laboratorio usare il percorso analysis con budget di sessione comune.')
        from .workflow import run_workflow
        from .market_client import delegate
        with lock:
            get_session(session_id)
        def request_view():
            return view(session_id, ViewRequest(scenario=Scenario.MORTGAGE, recipient="markets"))
        def cleanup():
            finish_session(session_id)
        async def authorized_delegate(task):
            return await broker.delegate(session_id, task, delegate)
        return await run_operation(session_id, request, lambda: run_workflow(request_view, authorized_delegate, cleanup))

    @app.post("/sessions/{session_id}/analysis")
    async def analysis(session_id: UUID, request: Request):
        return await run_operation(session_id, request, lambda: execute_analysis(session_id))

    async def execute_analysis(session_id):
        from .multi_workflow import run_analysis
        from .report import build_report
        from .market_client import delegate as markets
        from .tax_client import delegate as tax
        with lock:
            session = get_session(session_id)
            scenarios = list(dict.fromkeys(s.value for s in session.scenarios))
        def request_view(scenario):
            return view(session_id, ViewRequest(scenario=Scenario(scenario), recipient="markets" if scenario=="S-01" else "tax"))
        def cleanup():
            finish_session(session_id)
        batch=None
        if runtime.SINGLE:
            from .baseline_client import BatchDelegate
            batch=BatchDelegate([s for s in scenarios if not issues(session.profile,Scenario(s))])
            markets=tax=batch.submit
        async def authorized_markets(task):
            return await broker.delegate(session_id, task, markets)
        async def authorized_tax(task):
            return await broker.delegate(session_id, task, tax)
        result = await run_analysis(scenarios, request_view, {"S-01":authorized_markets,"S-02":authorized_tax}, cleanup,
                                    lambda activities,status:build_report(session.profile,scenarios,activities,status))
        request_outcome(result['status'])
        if runtime.EXPERIMENT!='off':
            result['workflow']=('single' if runtime.SINGLE else 'multi')+'-experiment-v1'
            result['experiment']={'protocol':'financial-profile-2x2-v1','organization':runtime.EXPERIMENT,'policy':runtime.MINIMIZATION,'sources':'fixed_local_fixtures','model':'llama3.2:3b','schedule':'sequential','session_budget_seconds':120,'model_calls_max':len(scenarios),'num_ctx':4096,'num_predict':200,'temperature':0,'keep_alive':0,'corpus':'synthetic-financial-v1'}
            if batch is not None:result['coordination_measurements']=batch.measurements
        result['trace_id'] = trace_id()
        # Presentazione ricavata dallo stesso JSON, senza inferenze e senza storico.
        # Un guasto di impaginazione non deve perdere il risultato strutturato valido.
        from .report_document import render_report_document
        try:
            with Span('presentation'):
                result['report_document_html'] = render_report_document(result['report'])
        except Exception:
            result['report_document_html'] = None
            result['presentation_warning'] = 'Documento leggibile non disponibile; il report JSON rimane utilizzabile.'
        return result

    @app.delete("/sessions/{session_id}", status_code=204)
    async def close_session(session_id: UUID):
        with lock:
            get_session(session_id)
            operation = stop_session(session_id, 'user_cancelled')
        if operation is not None:
            done, _ = await asyncio.wait({operation['task']}, timeout=CANCELLATION_GRACE_SECONDS)
            if not done:
                raise HTTPException(503, {'error_code':'cancellation_pending', 'session_closed':True,
                                          'message':'Accessi revocati; arresto dell’attività ancora in corso.'})
        return Response(status_code=204)

    return app


app = create_app()
