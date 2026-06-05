from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional
import json
import sqlite3

from .config import get_db_path


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def from_json(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def fetch_all(query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]


def fetch_one(query: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
    with connect() as connection:
        row = connection.execute(query, tuple(params)).fetchone()
        return dict(row) if row else None


def execute(query: str, params: Iterable[Any] = ()) -> None:
    with connect() as connection:
        connection.execute(query, tuple(params))


def init_db() -> Path:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS framework_dimensions (
              code TEXT PRIMARY KEY,
              dimension TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS framework_secondary_dimensions (
              id TEXT PRIMARY KEY,
              dimension TEXT NOT NULL,
              secondary_dimension TEXT NOT NULL,
              sort_order INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_entries (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              content TEXT NOT NULL,
              source_file_name TEXT,
              source_type TEXT,
              tags_json TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS generation_jobs (
              id TEXT PRIMARY KEY,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              requirement TEXT,
              target_dimensions_json TEXT NOT NULL DEFAULT '[]',
              target_secondary_dimensions_json TEXT NOT NULL DEFAULT '[]',
              target_tags_json TEXT NOT NULL DEFAULT '[]',
              count INTEGER NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              completed_at TEXT,
              error TEXT
            );

            CREATE TABLE IF NOT EXISTS question_drafts (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              question TEXT NOT NULL,
              scenario TEXT NOT NULL,
              options_json TEXT NOT NULL,
              correct_answer TEXT NOT NULL,
              explanation TEXT NOT NULL,
              dimension TEXT NOT NULL,
              secondary_dimension TEXT NOT NULL,
              sub_skill TEXT NOT NULL,
              cognitive_level TEXT NOT NULL,
              difficulty_estimate TEXT NOT NULL,
              tags_json TEXT NOT NULL DEFAULT '[]',
              source_reference TEXT,
              status TEXT NOT NULL,
              source_knowledge_ids_json TEXT NOT NULL DEFAULT '[]',
              generation_requirement TEXT,
              generation_job_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS questions (
              id TEXT PRIMARY KEY,
              item_code TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              question TEXT NOT NULL,
              scenario TEXT NOT NULL,
              options_json TEXT NOT NULL,
              correct_answer TEXT NOT NULL,
              explanation TEXT NOT NULL,
              dimension TEXT NOT NULL,
              secondary_dimension TEXT NOT NULL,
              sub_skill TEXT NOT NULL,
              cognitive_level TEXT NOT NULL,
              difficulty_estimate TEXT NOT NULL,
              tags_json TEXT NOT NULL DEFAULT '[]',
              source_reference TEXT,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
    return get_db_path()
