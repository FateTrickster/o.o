from typing import List

from .config import get_xfyun_model
from .database import init_db
from .llm_client import generate_with_xfyun
from .prompt_builder import build_generation_requirement
from .repositories import (
    complete_generation_job,
    create_drafts,
    create_generation_job,
    get_knowledge,
    seed_framework,
)
from .schemas import GenerateDraftRequest, KnowledgeEntry, QuestionDraft


async def generate_drafts(request: GenerateDraftRequest) -> List[QuestionDraft]:
    init_db()
    seed_framework()

    knowledge_entries: List[KnowledgeEntry] = []
    for knowledge_id in request.knowledgeIds:
        entry = get_knowledge(knowledge_id)
        if entry:
            knowledge_entries.append(entry)

    if not knowledge_entries:
        raise ValueError("No usable knowledge entries found")

    provider = request.provider or "xfyun"
    if provider != "xfyun":
        raise ValueError("The Python MVP currently supports provider='xfyun' only")

    model = request.model or get_xfyun_model()
    job = create_generation_job(
        provider=provider,
        model=model,
        requirement=request.requirement,
        target_dimensions=request.targetDimensions,
        target_secondary_dimensions=request.targetSecondaryDimensions,
        target_tags=request.targetTags,
        count=request.count,
    )

    try:
        questions = await generate_with_xfyun(request, knowledge_entries)
        drafts = create_drafts(
            questions=questions[: request.count],
            source_knowledge_ids=request.knowledgeIds,
            generation_requirement=build_generation_requirement(request),
            generation_job_id=job.id,
        )
        complete_generation_job(job.id, "completed")
        return drafts
    except Exception as exc:
        complete_generation_job(job.id, "failed", str(exc) or exc.__class__.__name__)
        raise
