"""API locale: avviare con un solo worker; inferenza locale tramite broker autorizzato."""
from contextlib import asynccontextmanager
from copy import deepcopy
from threading import RLock
from time import monotonic, perf_counter
from uuid import UUID, uuid4

import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse

from .inference import InferenceBroker, InferenceRequest
from .tool_egress import ToolRequest, SourceRequest, authorize_tool, source_request
from .a2a_egress import EgressDenied
from .models import SessionInput, ViewRequest, Scenario
from .pdf_input import extract_profile, PDFInputError
from .policy import POLICY_VERSION, issues, make_view

SESSION_TTL_SECONDS = 1800


def create_app() -> FastAPI:
    sessions = {}
    broker = InferenceBroker()
    lock = RLock()

    @asynccontextmanager
    async def lifespan(app):
        yield
        with lock:
            sessions.clear()
            broker.revoke()

    app = FastAPI(title="Gateway locale sperimentale", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Non riflettere nel messaggio i valori o il corpo della richiesta.
        return JSONResponse(status_code=422, content={"detail": "Ingresso non conforme allo schema; controllare campi, tipi e categorie."})

    def get_session(session_id):
        expired = [key for key, (_, deadline) in sessions.items() if deadline <= monotonic()]
        for key in expired:
            del sessions[key]
            broker.revoke(key)
        if session_id not in sessions:
            raise HTTPException(404, "Sessione assente o scaduta")
        return sessions[session_id][0]

    @app.post("/internal/inference")
    async def inference(payload: InferenceRequest, request: Request):
        try:
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
            return authorize_tool(broker, payload, request.headers.get('authorization'))
        except EgressDenied:
            raise HTTPException(403, "Strumento non autorizzato dal gateway.") from None

    @app.post("/internal/sources")
    async def source_proxy(payload: SourceRequest, request: Request):
        try:
            return await source_request(broker, payload, request.headers.get('authorization'))
        except EgressDenied:
            raise HTTPException(403, "Fonte non autorizzata dal gateway.") from None
        except (TimeoutError, httpx.TimeoutException):
            raise HTTPException(504, "Tempo massimo fonte superato.") from None
        except Exception:
            raise HTTPException(502, "Fonte non disponibile.") from None

    @app.get("/health")
    def health():
        return {"status": "ok", "policy_version": POLICY_VERSION}

    @app.post("/sessions", status_code=201)
    def create_session(payload: SessionInput):
        with lock:
            # Pulizia pigra anche in creazione; nessuna persistenza su disco.
            for key in [k for k, (_, end) in sessions.items() if end <= monotonic()]:
                del sessions[key]
                broker.revoke(key)
            sid = uuid4()
            sessions[sid] = (deepcopy(payload), monotonic() + SESSION_TTL_SECONDS)
            return {"session_id": str(sid), "policy_version": POLICY_VERSION,
                    "scenarios": {s.value: {"ready": not issues(payload.profile, s), "issues": issues(payload.profile, s)} for s in set(payload.scenarios)}}

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.post("/sessions/pdf", status_code=201)
    async def upload_pdf(files: list[UploadFile] = File(...), scenarios: list[Scenario] = Form(...)):
        try:
            if not 1 <= len(files) <= 4:
                raise HTTPException(400, "Caricare da uno a quattro PDF dello stesso fascicolo.")
            contents = []
            rejected_documents = []
            for index, file in enumerate(files, 1):
                content = await file.read(5 * 1024 * 1024 + 1)
                if len(content) > 5 * 1024 * 1024:
                    raise HTTPException(413, "Ogni PDF deve essere inferiore a 5 MiB.")
                try:
                    # Prevalidazione separata: un file rifiutato non entra nell'aggregazione.
                    extract_profile([content])
                except PDFInputError as exc:
                    rejected_documents.append({'upload_index': index, 'reason': str(exc)})
                    continue
                contents.append(content)
            if not contents:
                raise HTTPException(400, {'message': 'Nessun PDF utilizzabile.', 'rejected_documents': rejected_documents})
            try:
                profile, documents = extract_profile(contents)
            except PDFInputError as exc:
                raise HTTPException(400, str(exc)) from None
            result = create_session(SessionInput(scenarios=scenarios, profile=profile))
            return {**result, "documents": documents, "rejected_documents": rejected_documents, "profile": profile.model_dump(mode="json")}
        finally:
            for file in files:
                await file.close()

    @app.post("/sessions/{session_id}/views")
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
    async def run_markets(session_id: UUID):
        from datetime import datetime, timedelta, timezone
        from .agent_contracts import MarketTask, MarketView
        from .market_client import delegate
        from .a2a_egress import EgressDenied
        started = perf_counter()
        permitted = view(session_id, ViewRequest(scenario=Scenario.MORTGAGE, recipient="markets"))
        view_ms = (perf_counter()-started)*1000
        task = MarketTask(correlation_id=uuid4(), deadline=datetime.now(timezone.utc) + timedelta(seconds=120),
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
    async def workflow(session_id: UUID):
        from .workflow import run_workflow
        from .market_client import delegate
        with lock:
            get_session(session_id)
        def request_view():
            return view(session_id, ViewRequest(scenario=Scenario.MORTGAGE, recipient="markets"))
        def cleanup():
            with lock:
                sessions.pop(session_id, None)
                broker.revoke(session_id)
        async def authorized_delegate(task):
            return await broker.delegate(session_id, task, delegate)
        return await run_workflow(request_view, authorized_delegate, cleanup)

    @app.post("/sessions/{session_id}/analysis")
    async def analysis(session_id: UUID):
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
            with lock:
                sessions.pop(session_id, None)
                broker.revoke(session_id)
        async def authorized_markets(task):
            return await broker.delegate(session_id, task, markets)
        async def authorized_tax(task):
            return await broker.delegate(session_id, task, tax)
        return await run_analysis(scenarios, request_view, {"S-01":authorized_markets,"S-02":authorized_tax}, cleanup,
                                  lambda activities,status:build_report(session.profile,scenarios,activities,status))

    @app.delete("/sessions/{session_id}", status_code=204)
    def close_session(session_id: UUID):
        with lock:
            get_session(session_id)
            del sessions[session_id]
            broker.revoke(session_id)
        return Response(status_code=204)

    return app


app = create_app()
