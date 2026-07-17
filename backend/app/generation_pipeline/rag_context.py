"""RAG 检索编排：为选中的知识点批量检索教材参考片段。

检索只在 runner 层发生一次；Provider 与 Prompt 层只消费已检索好的上下文。
本模块导入 RAG 检索链（duckdb/numpy/openai），应仅在 use_rag=True 时被导入。
"""

from __future__ import annotations

from typing import Dict, List

from backend.app.rag.retriever import search_chunks

from .types import KnowledgePointContext, TaskSpec

RAG_TOP_K_MIN = 1
RAG_TOP_K_MAX = 5


def build_knowledge_query(
    knowledge_point: KnowledgePointContext,
    task: TaskSpec,
) -> str:
    """为单个知识点构造稳定的检索查询文本，空字段不输出。"""
    point = knowledge_point
    lines: List[str] = []

    stage = (point.stage or task.stage or "").strip()
    if stage:
        lines.append(f"学段：{stage}")
    name = (point.knowledge_point or "").strip()
    if name:
        lines.append(f"知识点：{name}")
    description = (point.description or "").strip()
    if description:
        lines.append(f"说明：{description}")
    topic = " / ".join(
        part.strip()
        for part in (point.primary_dimension, point.secondary_dimension, point.tertiary_ability)
        if part and part.strip()
    )
    if topic:
        lines.append(f"主题：{topic}")
    tags = [tag.strip() for tag in point.tags if tag and tag.strip()]
    if tags:
        lines.append(f"标签：{'、'.join(tags)}")
    requirement = (task.requirement or "").strip()
    if requirement:
        lines.append(f"出题要求：{requirement}")

    if not lines:
        raise ValueError(
            f"knowledge point {point.knowledge_code!r} has no usable text fields "
            "to build a RAG query"
        )
    return "\n".join(lines)


def retrieve_rag_contexts(
    knowledge_points: List[KnowledgePointContext],
    task: TaskSpec,
    top_k: int,
) -> Dict[str, List[dict]]:
    """按知识点检索教材 Chunk，返回 {knowledge_code: [chunk, ...]}。

    相同查询文本只调用一次 Embedding API；同一知识点的结果按 rank
    顺序保留并按 chunk_id 去重。检索失败时异常向上传递，管线应失败
    而不是静默退回无 RAG 出题。
    """
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not (
        RAG_TOP_K_MIN <= top_k <= RAG_TOP_K_MAX
    ):
        raise ValueError(
            f"rag_top_k must be an integer between {RAG_TOP_K_MIN} and {RAG_TOP_K_MAX}, "
            f"got {top_k!r}"
        )

    contexts: Dict[str, List[dict]] = {}
    cache: Dict[str, List[dict]] = {}

    for point in knowledge_points:
        knowledge_code = (point.knowledge_code or "").strip()
        if not knowledge_code:
            raise ValueError(
                f"knowledge point {point.knowledge_point!r} has an empty knowledge_code; "
                "cannot build a stable RAG context key"
            )

        query = build_knowledge_query(point, task)
        if query in cache:
            chunks = cache[query]
        else:
            chunks = search_chunks(query, top_k=top_k)
            cache[query] = chunks

        seen_ids: set[str] = set()
        deduped: List[dict] = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            if not chunk_id or not isinstance(chunk_id, str):
                raise RuntimeError(
                    f"RAG retrieval returned a result without a valid chunk_id "
                    f"for knowledge point {knowledge_code!r}"
                )
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            deduped.append(chunk)
            if len(deduped) >= top_k:
                break
        contexts[knowledge_code] = deduped

    return contexts
