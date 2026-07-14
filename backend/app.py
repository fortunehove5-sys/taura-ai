"""FastAPI backend for the Taura AI web demo.

Exposes:
  POST /api/chat    { session_id, message }  -> { language, intent, response, escalated }
  GET  /api/health   -> { status: "ok" }
  GET  /             -> serves webapp/index.html (a simple WhatsApp-style chat UI)

Run locally:
    uvicorn backend.app:app --reload --port 8000

Or via Docker: see Dockerfile / docker-compose.yml in the repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make src/ importable when running "uvicorn backend.app:app" from repo root.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from taura.orchestrator import Orchestrator  # noqa: E402

app = FastAPI(title="Taura AI Demo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only -- restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()

WEBAPP_DIR = ROOT_DIR / "webapp"
if WEBAPP_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEBAPP_DIR)), name="static")


class ChatRequest(BaseModel):
    session_id: str
    message: str
    channel: str = "whatsapp"


class ChatResponse(BaseModel):
    language: str
    intent: str
    response: str
    escalated: bool
    retrieved_source_id: str | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    result = orchestrator.handle_turn(req.session_id, req.channel, req.message)
    return ChatResponse(
        language=result.language,
        intent=result.intent,
        response=result.response_text,
        escalated=result.escalated,
        retrieved_source_id=result.retrieved_source_id,
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(WEBAPP_DIR / "index.html"))
