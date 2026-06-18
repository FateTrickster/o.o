from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from backend.app.config import get_deepseek_model, get_xfyun_model
from backend.app.repositories import (
    complete_generation_batch,
    complete_generation_job,
    create_drafts,
    create_generation_batch,
    create_generation_job,
)
from backend.app.schemas import QuestionInput, QuestionOption

from .task_config import task_to_dict
from .types import PipelineCandidate, TaskSpec


def _model_for_provider(provider: str) -> str:
    if provider == "xfyun":
        return get_xfyun_model()
    if provider == "deepseek":
        return get_deepseek_model()
    return provider


def _reference_answer(candidate: PipelineCandidate) -> str:
    question = candidate.question
    option_text = next(
        (option.get("text", "") for option in question.options if option.get("id") == question.correct_answer),
        "",
    )
    return f"{question.correct_answer}. {option_text}".strip()


def _candidate_tags(candidate: PipelineCandidate) -> List[str]:
    review = candidate.review
    tags = [
        *candidate.question.tags,
        "pipeline",
        f"structure:{review.structure_result}",
        f"quality:{review.quality_level}",
        "pipeline:passed" if review.passed else "pipeline:blocked",
    ]
    if review.duplicate_group:
        tags.append("duplicate")
    return list(dict.fromkeys(tag for tag in tags if tag))


def candidate_to_question_input(candidate: PipelineCandidate) -> QuestionInput:
    question = candidate.question
    point = candidate.knowledge_point
    return QuestionInput(
        questionType=question.question_type,
        title=question.title,
        question=question.question,
        scenario=question.scenario,
        options=[QuestionOption(id=option.get("id", ""), text=option.get("text", "")) for option in question.options],
        correctAnswer=question.correct_answer,
        explanation=question.explanation,
        dimension=question.dimension or point.primary_dimension,
        secondaryDimension=question.secondary_dimension or point.secondary_dimension,
        tertiaryDimension=question.tertiary_dimension or point.tertiary_ability,
        quaternaryDimension=question.quaternary_dimension or point.knowledge_point,
        subSkill=question.tertiary_dimension or point.tertiary_ability or question.secondary_dimension or point.secondary_dimension,
        cognitiveLevel=candidate.review.cognitive_level,
        difficultyEstimate=candidate.review.difficulty_estimate,
        tags=_candidate_tags(candidate),
        knowledgePoints=question.knowledge_points or [point.knowledge_point],
        sourceReference=question.source_reference or "；".join(point.source_references),
        status="draft",
        stage=point.stage,
        knowledgeCode=point.knowledge_code,
        primaryDimension=point.primary_dimension,
        tertiaryAbility=point.tertiary_ability,
        knowledgePoint=point.knowledge_point,
        questionTask=question.question,
        referenceAnswer=_reference_answer(candidate),
        scoringCriteria="单选题，选择一个最符合题意的选项。" if question.question_type in {"单选", "单选题"} else "",
        form="文本",
        sourceSheet=point.source_sheet,
        sourceRow=point.source_row,
    )


def write_passed_candidates(candidates: Iterable[PipelineCandidate], task: TaskSpec) -> int:
    accepted = [candidate for candidate in candidates if candidate.review.passed]
    if not accepted:
        return 0

    by_provider: Dict[str, List[PipelineCandidate]] = defaultdict(list)
    for candidate in accepted:
        by_provider[candidate.question.provider].append(candidate)

    created_total = 0
    requirement = task.requirement or f"pipeline task: {task_to_dict(task)}"

    for provider, provider_candidates in by_provider.items():
        job = create_generation_job(
            provider=provider,
            model=_model_for_provider(provider),
            requirement=requirement,
            target_dimensions=task.dimensions,
            target_secondary_dimensions=task.secondary_dimensions,
            target_tags=[],
            count=len(provider_candidates),
        )
        batch = create_generation_batch(
            job_id=job.id,
            batch_index=1,
            provider=provider,
            model=_model_for_provider(provider),
            planned_count=len(provider_candidates),
        )
        try:
            questions = [candidate_to_question_input(candidate) for candidate in provider_candidates]
            source_ids = list(dict.fromkeys(candidate.knowledge_point.id for candidate in provider_candidates))
            drafts = create_drafts(
                questions=questions,
                source_knowledge_ids=source_ids,
                generation_requirement=requirement,
                generation_job_id=job.id,
            )
            for candidate, draft in zip(provider_candidates, drafts):
                candidate.draft_id = draft.id
            created_total += len(drafts)
            complete_generation_batch(batch.id, "completed", len(drafts))
            complete_generation_job(job.id, "completed")
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            complete_generation_batch(batch.id, "failed", 0, message)
            complete_generation_job(job.id, "failed", message)
            raise

    return created_total
