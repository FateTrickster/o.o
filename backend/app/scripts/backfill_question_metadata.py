from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.config import get_db_path
from backend.app.database import init_db
from backend.app.scripts.import_workbook_questions import _match_knowledge_point


def _from_json(value: str, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _load_points(connection: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT knowledge_code, stage, primary_dimension, secondary_dimension,
               tertiary_ability, knowledge_point, description, source_row
        FROM knowledge_points
        ORDER BY stage ASC, primary_dimension ASC, source_row ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _parse_source_reference(value: str) -> tuple[str, int]:
    match = re.search(r"/\s*([^/]+?)\s*/\s*第(\d+)行", value or "")
    if not match:
        return "", 0
    return match.group(1).strip(), int(match.group(2))


def _question_form(options_json: str, question_type: str) -> str:
    options = _from_json(options_json, [])
    if options:
        return "选择题"
    if any(token in question_type for token in ["单选", "多选", "判断", "填空"]):
        return "客观题"
    return "文本"


def _pick_knowledge_raw(row: Dict[str, Any]) -> str:
    points = _from_json(row["knowledge_points_json"], [])
    for value in [row["knowledge_point"], row["quaternary_dimension"], *points]:
        if value:
            return str(value)
    return ""


def backfill(dry_run: bool = False) -> Dict[str, int]:
    init_db()
    stats = {"checked": 0, "updated": 0, "matchedKnowledgeCode": 0}
    with sqlite3.connect(str(get_db_path())) as connection:
        connection.row_factory = sqlite3.Row
        points = _load_points(connection)
        rows = connection.execute("SELECT * FROM questions ORDER BY item_code ASC").fetchall()
        for raw_row in rows:
            row = dict(raw_row)
            stats["checked"] += 1
            source_sheet, source_row = _parse_source_reference(row["source_reference"] or "")
            stage = row["stage"] or ("初中" if source_sheet else "")
            primary_dimension = row["primary_dimension"] or row["dimension"]
            form = row["form"] or _question_form(row["options_json"], row["question_type"] or "")
            knowledge_raw = _pick_knowledge_raw(row)
            context = " ".join(
                [
                    row["title"],
                    row["question"],
                    row["scenario"],
                    row["secondary_dimension"],
                    row["sub_skill"],
                    knowledge_raw,
                ]
            )
            matched = None
            if stage:
                matched = _match_knowledge_point(points, stage, primary_dimension, knowledge_raw, context)

            updates = {
                "stage": stage,
                "primary_dimension": primary_dimension,
                "knowledge_code": row["knowledge_code"],
                "tertiary_ability": row["tertiary_ability"] or row["tertiary_dimension"] or "",
                "knowledge_point": row["knowledge_point"] or row["quaternary_dimension"] or knowledge_raw,
                "question_task": row["question_task"],
                "reference_answer": row["reference_answer"] or row["correct_answer"],
                "scoring_criteria": row["scoring_criteria"],
                "form": form,
                "source_sheet": row["source_sheet"] or source_sheet,
                "source_row": row["source_row"] or source_row,
            }
            if matched:
                updates.update(
                    {
                        "knowledge_code": matched["knowledge_code"],
                        "primary_dimension": matched["primary_dimension"],
                        "secondary_dimension": matched["secondary_dimension"],
                        "tertiary_ability": matched["tertiary_ability"],
                        "knowledge_point": matched["knowledge_point"],
                    }
                )
                stats["matchedKnowledgeCode"] += 1

            changed = any(row.get(column) != value for column, value in updates.items())
            if not changed:
                continue
            stats["updated"] += 1
            if dry_run:
                continue
            connection.execute(
                """
                UPDATE questions
                SET stage = ?,
                    knowledge_code = ?,
                    primary_dimension = ?,
                    secondary_dimension = ?,
                    tertiary_ability = ?,
                    knowledge_point = ?,
                    question_task = ?,
                    reference_answer = ?,
                    scoring_criteria = ?,
                    form = ?,
                    source_sheet = ?,
                    source_row = ?
                WHERE id = ?
                """,
                (
                    updates["stage"],
                    updates["knowledge_code"],
                    updates["primary_dimension"],
                    updates.get("secondary_dimension", row["secondary_dimension"]),
                    updates["tertiary_ability"],
                    updates["knowledge_point"],
                    updates["question_task"],
                    updates["reference_answer"],
                    updates["scoring_criteria"],
                    updates["form"],
                    updates["source_sheet"],
                    updates["source_row"],
                    row["id"],
                ),
            )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill normalized question metadata columns.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = backfill(dry_run=args.dry_run)
    print(f"dry_run={args.dry_run}")
    for key, value in stats.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
