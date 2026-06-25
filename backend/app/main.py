from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException

from .config import ROOT_DIR, get_db_path, get_xfyun_model
from .database import init_db
from .framework import UACE_FRAMEWORK
from .generation_pipeline.report import candidate_to_row
from .generation_pipeline.runner import run_pipeline as run_question_pipeline
from .generation_pipeline.types import TaskSpec
from .pipeline import generate_drafts as run_generate_drafts
from .repositories import (
    accept_draft,
    list_generation_batches,
    list_knowledge_points,
    list_knowledge_taxonomy,
    list_question_type_examples,
    list_question_types,
    create_knowledge,
    create_knowledge_many,
    create_question,
    delete_draft,
    delete_knowledge,
    delete_question,
    filter_questions,
    get_draft,
    get_knowledge,
    get_question,
    import_questions,
    list_drafts,
    list_generation_jobs,
    list_knowledge,
    list_questions,
    seed_framework,
    update_draft,
    update_knowledge,
    update_question,
)
from .schemas import (
    GenerateDraftRequest,
    GenerationBatch,
    GenerationJob,
    ImportKnowledgeResult,
    ImportJsonRequest,
    ImportQuestionsResult,
    KnowledgeEntry,
    KnowledgeInput,
    KnowledgePoint,
    KnowledgeTaxonomyItem,
    Question,
    QuestionDraft,
    QuestionInput,
    QuestionPipelineRunRequest,
    QuestionPipelineRunResult,
    QuestionType,
    QuestionTypeExample,
)
from .seed import initialize_from_json


app = FastAPI(
    title="AI Literacy Question Pipeline",
    version="0.1.0",
    description="Python MVP for AI literacy draft generation and SQLite persistence.",
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed_framework()


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


@app.get("/question-types", response_model=List[QuestionType])
def get_question_types():
    return list_question_types()


@app.get("/question-type-examples", response_model=List[QuestionTypeExample])
def get_question_type_examples(questionType: Optional[str] = None):
    return list_question_type_examples(questionType)


@app.get("/knowledge-taxonomy", response_model=List[KnowledgeTaxonomyItem])
def get_knowledge_taxonomy(
    gradeLevel: Optional[str] = None,
    primaryDimension: Optional[str] = None,
    secondaryDimension: Optional[str] = None,
):
    return list_knowledge_taxonomy(gradeLevel, primaryDimension, secondaryDimension)


@app.get("/knowledge-points", response_model=List[KnowledgePoint])
def get_knowledge_points(
    stage: Optional[str] = None,
    primaryDimension: Optional[str] = None,
    secondaryDimension: Optional[str] = None,
    search: Optional[str] = None,
):
    return list_knowledge_points(stage, primaryDimension, secondaryDimension, search)


@app.get("/knowledge", response_model=List[KnowledgeEntry])
def get_knowledge_entries(
    sourceType: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
):
    entries = list_knowledge()
    normalized_tag = tag.strip().lower() if tag else ""
    normalized_search = search.strip().lower() if search else ""
    filtered: List[KnowledgeEntry] = []

    for entry in entries:
        if sourceType and entry.sourceType != sourceType:
            continue
        if normalized_tag and not any(normalized_tag in item.lower() for item in entry.tags):
            continue
        if normalized_search:
            haystack = " ".join(
                [entry.title, entry.content, entry.sourceFileName, entry.sourceType, " ".join(entry.tags)]
            ).lower()
            if normalized_search not in haystack:
                continue
        filtered.append(entry)

    return filtered


@app.post("/knowledge", response_model=KnowledgeEntry)
def create_knowledge_entry(request: KnowledgeInput):
    return create_knowledge(request)


@app.post("/knowledge/import", response_model=ImportKnowledgeResult)
def import_knowledge_entries(request: List[KnowledgeInput]):
    return create_knowledge_many(request)


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


@app.get("/generation-jobs", response_model=List[GenerationJob])
def get_generation_jobs():
    return list_generation_jobs()


@app.get("/generation-batches", response_model=List[GenerationBatch])
def get_generation_batches(jobId: Optional[str] = None):
    return list_generation_batches(jobId)


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


@app.post("/question-pipeline/run", response_model=QuestionPipelineRunResult)
async def run_question_generation_pipeline(request: QuestionPipelineRunRequest):
    task = TaskSpec(
        name=request.name,
        stage=request.stage,
        dimensions=request.dimensions,
        secondary_dimensions=request.secondaryDimensions,
        knowledge_codes=request.knowledgeCodes,
        providers=request.providers,
        question_type=request.questionType,
        count_per_knowledge_point=request.countPerKnowledgePoint,
        limit_per_dimension=request.limitPerDimension,
        max_knowledge_points=request.maxKnowledgePoints,
        difficulty_target=request.difficultyTarget,
        cognitive_level_target=request.cognitiveLevelTarget,
        requirement=request.requirement,
        prompt_batch_size=request.promptBatchSize,
        similarity_threshold=request.similarityThreshold,
        write_drafts=request.writeDrafts,
        output_dir=request.outputDir,
    )
    try:
        report = await run_question_pipeline(task)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return QuestionPipelineRunResult(
        selectedKnowledgePoints=len(report.selected_points),
        generatedCandidates=len(report.candidates),
        createdDrafts=report.created_drafts,
        errors=report.errors,
        reportJson=report.report_json,
        reportCsv=report.report_csv,
        candidates=[candidate_to_row(index, candidate) for index, candidate in enumerate(report.candidates, start=1)],
    )


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
def get_questions(
    dimension: Optional[str] = None,
    secondaryDimension: Optional[str] = None,
    status: Optional[str] = None,
    difficulty: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
):
    if any([dimension, secondaryDimension, status, difficulty, tag, search]):
        return filter_questions(
            dimension=dimension,
            secondary_dimension=secondaryDimension,
            status=status,
            difficulty=difficulty,
            tag=tag,
            search=search,
        )
    return list_questions()


@app.post("/questions", response_model=Question)
def create_formal_question(request: QuestionInput):
    return create_question(request)


@app.post("/questions/import", response_model=ImportQuestionsResult)
def import_formal_questions(request: List[Dict]):
    return import_questions(request)


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
