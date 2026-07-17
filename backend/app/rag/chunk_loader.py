"""
Zhishitupu textbook chunk JSON loader.
Reads *.chunks.json files produced by markdown_to_chunks_json.py,
validates structure, and returns chunk records ready for Document mapping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_chunk_file(filepath: Path) -> list[dict[str, Any]]:
    """Load and validate a single *.chunks.json file. Returns list of chunk dicts."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{filepath.name}: top-level must be a JSON array, got {type(data).__name__}")
    for i, chunk in enumerate(data):
        validate_chunk(chunk, filepath.name, i)
    return data


def load_chunk_directory(chunk_dir: Path) -> list[dict[str, Any]]:
    """Load all *.chunks.json files from a directory in stable order."""
    files = sorted(chunk_dir.glob("*.chunks.json"))
    if not files:
        raise FileNotFoundError(f"No *.chunks.json files found in {chunk_dir}")
    all_chunks: list[dict[str, Any]] = []
    for fp in files:
        all_chunks.extend(load_chunk_file(fp))
    validate_chunk_collection(all_chunks)
    return all_chunks


_REQUIRED_FIELDS = {
    "chunk_id", "book_name", "source_file", "section_id",
    "chunk_index", "heading_path", "content",
}


def validate_chunk(chunk: dict[str, Any], filename: str = "", index: int = 0) -> None:
    """Validate a single chunk record. Raises ValueError on failure."""
    prefix = f"{filename}[{index}]" if filename else f"chunk[{index}]"

    # Check required fields
    missing = _REQUIRED_FIELDS - set(chunk.keys())
    if missing:
        raise ValueError(f"{prefix}: missing fields: {missing}")

    # chunk_id: non-empty string
    if not isinstance(chunk["chunk_id"], str) or not chunk["chunk_id"].strip():
        raise ValueError(f"{prefix}: chunk_id must be a non-empty string")

    # content: non-empty string
    if not isinstance(chunk["content"], str) or not chunk["content"].strip():
        raise ValueError(f"{prefix}: content must be a non-empty string")

    # book_name: non-empty string
    if not isinstance(chunk["book_name"], str) or not chunk["book_name"].strip():
        raise ValueError(f"{prefix}: book_name must be a non-empty string")

    # source_file: non-empty string
    if not isinstance(chunk["source_file"], str) or not chunk["source_file"].strip():
        raise ValueError(f"{prefix}: source_file must be a non-empty string")

    # section_id: non-empty string
    if not isinstance(chunk["section_id"], str) or not chunk["section_id"].strip():
        raise ValueError(f"{prefix}: section_id must be a non-empty string")

    # chunk_index: positive integer
    ci = chunk["chunk_index"]
    if not isinstance(ci, int) or ci < 1:
        raise ValueError(f"{prefix}: chunk_index must be a positive integer, got {ci!r}")

    # heading_path: array of {level, title}
    hp = chunk["heading_path"]
    if not isinstance(hp, list):
        raise ValueError(f"{prefix}: heading_path must be an array")
    for j, node in enumerate(hp):
        if not isinstance(node, dict):
            raise ValueError(f"{prefix}: heading_path[{j}] must be an object")
        if "level" not in node or "title" not in node:
            raise ValueError(f"{prefix}: heading_path[{j}] missing 'level' or 'title'")
        if not isinstance(node["level"], int) or not (1 <= node["level"] <= 6):
            raise ValueError(
                f"{prefix}: heading_path[{j}].level must be 1-6, got {node['level']!r}"
            )
        if not isinstance(node["title"], str) or not node["title"].strip():
            raise ValueError(f"{prefix}: heading_path[{j}].title must be a non-empty string")


def validate_chunk_collection(chunks: list[dict[str, Any]]) -> None:
    """Validate global constraints: unique chunk_ids, continuous chunk_index per section."""
    seen_ids: set[str] = set()
    section_indices: dict[tuple[str, str], list[int]] = {}

    for chunk in chunks:
        cid = chunk["chunk_id"]
        if cid in seen_ids:
            raise ValueError(f"Duplicate chunk_id: {cid}")
        seen_ids.add(cid)

        key = (chunk["source_file"], chunk["section_id"])
        section_indices.setdefault(key, []).append(chunk["chunk_index"])

    for (book, sid), indices in section_indices.items():
        sorted_idx = sorted(indices)
        expected = list(range(1, len(sorted_idx) + 1))
        if sorted_idx != expected:
            raise ValueError(
                f"[{book}] section {sid}: chunk_index not contiguous. "
                f"Got {sorted_idx}, expected {expected}"
            )
