"""RAG 检索模块：查询文本 → 查询向量 → DuckDB 余弦相似度 → Top-K 教材 Chunk。

直接以只读方式读取 DuckDB 向量库，不依赖 RAGLite ORM，不生成问答。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import duckdb
import numpy as np

from backend.app.config import get_rag_database_path
from backend.app.rag.embedding import EmbeddingClient


def search_chunks(
    query: str,
    top_k: int = 5,
    database_path: Path | None = None,
) -> list[dict[str, object]]:
    """检索与查询文本最相关的 Top-K 教材 Chunk，按相似度降序返回。"""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    _validate_top_k(top_k)

    query_vector = EmbeddingClient().embed([query])[0]
    return _search_by_vector(query_vector, top_k, database_path)


def _search_by_vector(
    query_vector: Sequence[float] | np.ndarray,
    top_k: int = 5,
    database_path: Path | None = None,
) -> list[dict[str, object]]:
    """用现成的查询向量执行检索。离线测试可绕过 Embedding API 直接调用。"""
    _validate_top_k(top_k)

    db_path = Path(database_path) if database_path is not None else get_rag_database_path()
    if not db_path.exists():
        raise FileNotFoundError(f"RAG database not found: {db_path}")

    query_vec = np.asarray(query_vector, dtype=np.float32).reshape(-1)
    if not np.all(np.isfinite(query_vec)):
        raise ValueError("query vector contains NaN or Inf values")
    query_norm = float(np.linalg.norm(query_vec))
    if query_norm == 0.0:
        raise ValueError("query vector must not be a zero vector")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute("SELECT chunk_id, embedding FROM chunk_embedding").fetchall()
        if not rows:
            raise RuntimeError(f"chunk_embedding table is empty: {db_path}")

        ids = [row[0] for row in rows]
        matrix = np.array([row[1] for row in rows], dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] != query_vec.shape[0]:
            raise ValueError(
                f"Embedding dimension mismatch: database has {matrix.shape[-1]}, "
                f"query vector has {query_vec.shape[0]}"
            )
        finite_rows = np.isfinite(matrix).all(axis=1)
        if not finite_rows.all():
            raise RuntimeError(
                f"database embeddings contain NaN/Inf in "
                f"{int(np.count_nonzero(~finite_rows))} rows"
            )

        norms = np.linalg.norm(matrix, axis=1)
        # 库内零向量无法参与余弦计算，相似度按 0 处理，避免除零警告。
        norms[norms == 0.0] = np.inf
        scores = (matrix @ query_vec) / (norms * query_norm)

        k = min(top_k, len(ids))
        # 分数降序；同分时按数据库 chunk_id 升序，保证结果可复现。
        order = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))[:k]

        selected_ids = [ids[i] for i in order]
        placeholders = ", ".join("?" for _ in selected_ids)
        meta_rows = con.execute(
            f"SELECT id, metadata FROM chunk WHERE id IN ({placeholders})",
            selected_ids,
        ).fetchall()
        raw_metadata = {row[0]: row[1] for row in meta_rows}
    finally:
        con.close()

    results: list[dict[str, object]] = []
    for rank, idx in enumerate(order, start=1):
        internal_id = ids[idx]
        if internal_id not in raw_metadata:
            raise RuntimeError(f"chunk row missing for embedding chunk_id: {internal_id}")
        results.append(
            _build_result(rank, float(scores[idx]), internal_id, raw_metadata[internal_id])
        )
    return results


def _validate_top_k(top_k: int) -> None:
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError(f"top_k must be a positive integer, got {top_k!r}")


def _build_result(
    rank: int, score: float, internal_id: str, raw_meta: object
) -> dict[str, object]:
    try:
        meta = json.loads(raw_meta) if raw_meta else {}
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"chunk.metadata is not valid JSON for {internal_id}") from exc
    if not isinstance(meta, dict):
        raise ValueError(f"chunk.metadata is not a JSON object for {internal_id}")

    chunk_id = meta.get("chunk_id")
    if not chunk_id:
        raise ValueError(f"metadata missing required field 'chunk_id' for database row {internal_id}")
    original_content = meta.get("original_content")
    if not original_content:
        raise ValueError(f"metadata missing required field 'original_content' for chunk {chunk_id}")

    heading_path_json = meta.get("heading_path_json") or "[]"
    try:
        heading_path = json.loads(heading_path_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"heading_path_json cannot be parsed for chunk {chunk_id}") from exc
    if not isinstance(heading_path, list):
        raise ValueError(f"heading_path_json is not a JSON array for chunk {chunk_id}")

    return {
        "rank": rank,
        "score": score,
        "chunk_id": str(chunk_id),
        "book_name": str(meta.get("book_name", "")),
        "source_file": str(meta.get("source_file", "")),
        "section_id": str(meta.get("section_id", "")),
        "chunk_index": int(meta.get("chunk_index", 1)),
        "heading_path_text": str(meta.get("heading_path_text", "")),
        "heading_path": heading_path,
        "original_content": str(original_content),
    }
