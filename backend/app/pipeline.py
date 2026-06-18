from typing import List

from .config import get_deepseek_model, get_xfyun_model
from .database import init_db
from .llm_client import generate_with_deepseek, generate_with_xfyun
from .prompt_builder import build_generation_requirement
from .repositories import (
    complete_generation_batch,
    complete_generation_job,
    create_generation_batch,
    create_drafts,
    create_generation_job,
    get_knowledge,
    seed_framework,
)
from .schemas import GenerateDraftRequest, KnowledgeEntry, QuestionDraft


BATCH_SIZE = 3


def _copy_request_with_count(request: GenerateDraftRequest, count: int) -> GenerateDraftRequest:
    return GenerateDraftRequest(
        knowledgeIds=request.knowledgeIds,
        requirement=request.requirement,
        targetDimensions=request.targetDimensions,
        targetSecondaryDimensions=request.targetSecondaryDimensions,
        targetTags=request.targetTags,
        count=count,
        provider=request.provider,
        model=request.model,
    )


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
    if provider == "xfyun":
        model = request.model or get_xfyun_model()
        generator = generate_with_xfyun
    elif provider == "deepseek":
        model = request.model or get_deepseek_model()
        generator = generate_with_deepseek
    else:
        raise ValueError("The Python MVP currently supports provider='xfyun' or provider='deepseek'")
    job = create_generation_job(
        provider=provider,
        model=model,
        requirement=request.requirement,
        target_dimensions=request.targetDimensions,
        target_secondary_dimensions=request.targetSecondaryDimensions,
        target_tags=request.targetTags,
        count=request.count,
    )

    drafts: List[QuestionDraft] = []
    errors: List[str] = []
    remaining = request.count
    batch_index = 1

    while remaining > 0:
        planned_count = min(BATCH_SIZE, remaining)
        batch = create_generation_batch(
            job_id=job.id,
            batch_index=batch_index,
            provider=provider,
            model=model,
            planned_count=planned_count,
        )
        batch_request = _copy_request_with_count(request, planned_count)

        try:
            questions = await generator(batch_request, knowledge_entries)
            batch_drafts = create_drafts(
                questions=questions[:planned_count],
                source_knowledge_ids=request.knowledgeIds,
                generation_requirement=build_generation_requirement(batch_request),
                generation_job_id=job.id,
            )
            drafts.extend(batch_drafts)
            complete_generation_batch(batch.id, "completed", len(batch_drafts))
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            errors.append(f"Batch {batch_index}: {message}")
            complete_generation_batch(batch.id, "failed", 0, message)

        remaining -= planned_count
        batch_index += 1

    if drafts:
        status = "completed" if not errors else "partial"
        complete_generation_job(job.id, status, "\n".join(errors) if errors else None)
        return drafts

    error_message = "\n".join(errors) or "No drafts were generated"
    complete_generation_job(job.id, "failed", error_message)
    raise RuntimeError(error_message)
