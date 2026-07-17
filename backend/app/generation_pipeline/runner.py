from __future__ import annotations

from typing import Any, Dict, Iterable, List

from backend.app.database import init_db
from backend.app.repositories import seed_framework

from .ai_review import ai_review_candidates
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


def _rag_usage_summary(
    task: TaskSpec,
    contexts: Dict[str, List[Dict[str, object]]],
) -> Dict[str, Any]:
    if not task.use_rag:
        return {"enabled": False}
    return {
        "enabled": True,
        "top_k": task.rag_top_k,
        "knowledge_point_count": len(contexts),
        "retrieved_chunk_count": sum(len(chunks) for chunks in contexts.values()),
        "references": [
            {
                "knowledge_code": knowledge_code,
                "chunk_id": chunk.get("chunk_id", ""),
                "book_name": chunk.get("book_name", ""),
                "heading_path_text": chunk.get("heading_path_text", ""),
                "rank": chunk.get("rank", 0),
                "score": chunk.get("score", 0.0),
            }
            for knowledge_code, chunks in contexts.items()
            for chunk in chunks
        ],
    }


async def run_pipeline(task: TaskSpec) -> PipelineReport:
    init_db()
    seed_framework()

    selected_points = select_knowledge_points(task)
    if not selected_points:
        raise ValueError("No knowledge points matched the task configuration.")

    rag_context_by_knowledge_code: Dict[str, List[Dict[str, object]]] = {}
    if task.use_rag:
        # 惰性导入：use_rag=False 时不加载 RAG 检索链（duckdb/numpy/openai）。
        from .rag_context import retrieve_rag_contexts

        rag_context_by_knowledge_code = retrieve_rag_contexts(
            selected_points, task, task.rag_top_k
        )

    generated: List[GeneratedQuestion] = []
    errors: List[str] = []

    for provider in task.providers:
        for batch_index, point_batch in enumerate(_chunks(selected_points, task.prompt_batch_size), start=1):
            try:
                generated.extend(
                    await generate_for_provider(
                        provider,
                        point_batch,
                        task,
                        rag_context_by_knowledge_code=rag_context_by_knowledge_code or None,
                    )
                )
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                errors.append(f"{provider} batch {batch_index}: {message}")

    point_by_code = {point.knowledge_code: point for point in selected_points}
    candidates = review_candidates(generated, point_by_code, task) if generated else []
    errors.extend(await ai_review_candidates(candidates, task))

    report = PipelineReport(
        task=task,
        selected_points=selected_points,
        candidates=candidates,
        errors=errors,
        rag_usage=_rag_usage_summary(task, rag_context_by_knowledge_code),
    )

    if task.write_drafts:
        report.created_drafts = write_passed_candidates(report.candidates, task)

    return write_report(report)
