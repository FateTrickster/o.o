from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException

from .config import ROOT_DIR, get_db_path, get_xfyun_model
from .database import init_db
from .framework import UACE_FRAMEWORK
from .pipeline import generate_drafts as run_generate_drafts
from .repositories import accept_draft, list_drafts, list_knowledge, list_questions, seed_framework
from .schemas import (
    GenerateDraftRequest,
    ImportJsonRequest,
    KnowledgeEntry,
    Question,
    QuestionDraft,
)
from .seed import initialize_from_json


app = FastAPI(
    title="AI Literacy Question Pipeline",
    version="0.1.0",
    description="Python MVP for AI literacy draft generation and SQLite persistence.",
)


@app.get("/health")
def health():
    return {
        "ok": True,
        "database": str(get_db_path()),
        "defaultModel": get_xfyun_model(),
    }


@app.post("/admin/init-db")
def admin_init_db():
    db_path = init_db()
    seed_framework()
    return {"ok": True, "database": str(db_path)}


@app.post("/admin/import-json")
def admin_import_json(request: ImportJsonRequest):
    counts = initialize_from_json(ROOT_DIR / "data", reset=request.reset)
    return {"ok": True, "imported": counts}


@app.get("/framework")
def get_framework():
    return UACE_FRAMEWORK


@app.get("/knowledge", response_model=List[KnowledgeEntry])
def get_knowledge_entries():
    return list_knowledge()


@app.get("/drafts", response_model=List[QuestionDraft])
def get_drafts():
    return list_drafts()


@app.post("/drafts/generate", response_model=List[QuestionDraft])
async def generate_drafts(request: GenerateDraftRequest):
    try:
        return await run_generate_drafts(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/drafts/{draft_id}/accept", response_model=Question)
def accept_generated_draft(draft_id: str):
    question = accept_draft(draft_id)
    if not question:
        raise HTTPException(status_code=404, detail="Draft not found")
    return question


@app.get("/questions", response_model=List[Question])
def get_questions():
    return list_questions()
