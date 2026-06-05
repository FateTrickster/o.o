from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException

from .config import ROOT_DIR, get_db_path, get_xfyun_model
from .database import init_db
from .framework import UACE_FRAMEWORK
from .pipeline import generate_drafts as run_generate_drafts
from .repositories import (
    accept_draft,
    create_knowledge,
    delete_draft,
    delete_knowledge,
    delete_question,
    get_draft,
    get_knowledge,
    get_question,
    list_drafts,
    list_knowledge,
    list_questions,
    seed_framework,
    update_draft,
    update_knowledge,
    update_question,
)
from .schemas import (
    GenerateDraftRequest,
    ImportJsonRequest,
    KnowledgeEntry,
    KnowledgeInput,
    Question,
    QuestionDraft,
    QuestionInput,
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


@app.post("/knowledge", response_model=KnowledgeEntry)
def create_knowledge_entry(request: KnowledgeInput):
    return create_knowledge(request)


@app.get("/knowledge/{entry_id}", response_model=KnowledgeEntry)
def get_one_knowledge_entry(entry_id: str):
    entry = get_knowledge(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@app.put("/knowledge/{entry_id}", response_model=KnowledgeEntry)
def update_knowledge_entry(entry_id: str, request: KnowledgeInput):
    entry = update_knowledge(entry_id, request)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@app.delete("/knowledge/{entry_id}")
def delete_knowledge_entry(entry_id: str):
    deleted = delete_knowledge(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return {"ok": True}


@app.get("/drafts", response_model=List[QuestionDraft])
def get_drafts():
    return list_drafts()


@app.get("/drafts/{draft_id}", response_model=QuestionDraft)
def get_one_draft(draft_id: str):
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.post("/drafts/generate", response_model=List[QuestionDraft])
async def generate_drafts(request: GenerateDraftRequest):
    try:
        return await run_generate_drafts(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/drafts/{draft_id}", response_model=QuestionDraft)
def update_generated_draft(draft_id: str, request: QuestionInput):
    draft = update_draft(draft_id, request)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.delete("/drafts/{draft_id}")
def delete_generated_draft(draft_id: str):
    deleted = delete_draft(draft_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"ok": True}


@app.post("/drafts/{draft_id}/accept", response_model=Question)
def accept_generated_draft(draft_id: str):
    question = accept_draft(draft_id)
    if not question:
        raise HTTPException(status_code=404, detail="Draft not found")
    return question


@app.get("/questions", response_model=List[Question])
def get_questions():
    return list_questions()


@app.get("/questions/{question_id}", response_model=Question)
def get_one_question(question_id: str):
    question = get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.put("/questions/{question_id}", response_model=Question)
def update_formal_question(question_id: str, request: QuestionInput):
    question = update_question(question_id, request)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.delete("/questions/{question_id}")
def delete_formal_question(question_id: str):
    deleted = delete_question(question_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"ok": True}
