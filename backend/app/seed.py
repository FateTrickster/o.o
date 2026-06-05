from pathlib import Path
from typing import Dict

from .database import connect, init_db
from .repositories import import_json_data, seed_framework


def reset_database() -> None:
    with connect() as connection:
        for table in [
            "framework_secondary_dimensions",
            "framework_dimensions",
            "knowledge_entries",
            "generation_jobs",
            "question_drafts",
            "questions",
        ]:
            connection.execute(f"DELETE FROM {table}")


def initialize_from_json(root_data_dir: Path, reset: bool = False) -> Dict[str, int]:
    init_db()
    if reset:
        reset_database()
    seed_framework()
    return import_json_data(root_data_dir)
