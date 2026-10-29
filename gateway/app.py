"""API locale: avviare con un solo worker; nessuna chiamata esterna."""
from contextlib import asynccontextmanager
from copy import deepcopy
from threading import RLock
from time import monotonic, perf_counter
from uuid import UUID, uuid4

from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse

from .models import SessionInput, ViewRequest, Scenario
from .pdf_input import extract_profile, PDFInputError
from .policy import POLICY_VERSION, issues, make_view

SESSION_TTL_SECONDS = 1800


def create_app() -> FastAPI:
    sessions = {}
    lock = RLock()

    @asynccontextmanager
    async def lifespan(app):
        yield
        with lock:
            sessions.clear()

    app = FastAPI(title="Gateway locale sperimentale", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Non riflettere nel messaggio i valori o il corpo della richiesta.
        return JSONResponse(status_code=422, content={"detail": "Ingresso non conforme allo schema; controllare campi, tipi e categorie."})

    def get_session(session_id):
        expired = [key for key, (_, deadline) in sessions.items() if deadline <= monotonic()]
        for key in expired:
            del sessions[key]
        if session_id not in sessions:
            raise HTTPException(404, "Sessione assente o scaduta")
        return sessions[session_id][0]

    @app.get("/health")
    def health():
        return {"status": "ok", "policy_version": POLICY_VERSION}

    @app.post("/sessions", status_code=201)
    def create_session(payload: SessionInput):
        with lock:
            # Pulizia pigra anche in creazione; nessuna persistenza su disco.
            for key in [k for k, (_, end) in sessions.items() if end <= monotonic()]:
                del sessions[key]
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
            for file in files:
                content = await file.read(5 * 1024 * 1024 + 1)
                if len(content) > 5 * 1024 * 1024:
                    raise HTTPException(413, "Ogni PDF deve essere inferiore a 5 MiB.")
                contents.append(content)
            try:
                profile, documents = extract_profile(contents)
            except PDFInputError as exc:
                raise HTTPException(400, str(exc)) from None
            result = create_session(SessionInput(scenarios=scenarios, profile=profile))
            return {**result, "documents": documents, "profile": profile.model_dump(mode="json")}
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
        started = perf_counter()
        permitted = view(session_id, ViewRequest(scenario=Scenario.MORTGAGE, recipient="markets"))
        view_ms = (perf_counter()-started)*1000
        task = MarketTask(correlation_id=uuid4(), deadline=datetime.now(timezone.utc) + timedelta(seconds=120),
                          view=MarketView.model_validate(permitted["data"]))
        try:
            result = await delegate(task)
        except Exception:
            raise HTTPException(502, "Delega non completata: controllare servizio mercati, Card e Ollama.") from None
        result.measurements.update({'view_ms':round(view_ms, 3), 'gateway_total_ms':round((perf_counter()-started)*1000, 3)})
        return result.model_dump(mode="json")

    @app.delete("/sessions/{session_id}", status_code=204)
    def close_session(session_id: UUID):
        with lock:
            get_session(session_id)
            del sessions[session_id]
        return Response(status_code=204)

    return app


app = create_app()
