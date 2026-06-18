from __future__ import annotations

from typing import Iterable, List

from backend.app.database import init_db
from backend.app.repositories import seed_framework

from .providers import generate_for_provider
from .report import write_report
from .review import review_candidates
from .selector import select_knowledge_points
from .types import GeneratedQuestion, KnowledgePointContext, PipelineReport, TaskSpec
from .writer import write_passed_candidates


def _chunks(items: List[KnowledgePointContext], size: int) -> Iterable[List[KnowledgePointContext]]:
    safe_size = max(1, size)
    for index in range(0, len(items), safe_size):
        yield items[index : index + safe_size]


async def run_pipeline(task: TaskSpec) -> PipelineReport:
    init_db()
    seed_framework()

    selected_points = select_knowledge_points(task)
    if not selected_points:
        raise ValueError("No knowledge points matched the task configuration.")

    generated: List[GeneratedQuestion] = []
    errors: List[str] = []

    for provider in task.providers:
        for batch_index, point_batch in enumerate(_chunks(selected_points, task.prompt_batch_size), start=1):
            try:
                generated.extend(await generate_for_provider(provider, point_batch, task))
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                errors.append(f"{provider} batch {batch_index}: {message}")

    point_by_code = {point.knowledge_code: point for point in selected_points}
    candidates = review_candidates(generated, point_by_code, task) if generated else []

    report = PipelineReport(
        task=task,
        selected_points=selected_points,
        candidates=candidates,
        errors=errors,
    )

    if task.write_drafts:
        report.created_drafts = write_passed_candidates(report.candidates, task)

    return write_report(report)
