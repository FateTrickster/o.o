from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from backend.app.database import now_iso

from .task_config import task_to_dict
from .types import PipelineCandidate, PipelineReport, TaskSpec


def _safe_timestamp() -> str:
    return now_iso().replace(":", "").replace("-", "").replace("Z", "Z")


def candidate_to_row(index: int, candidate: PipelineCandidate) -> Dict[str, Any]:
    question = candidate.question
    point = candidate.knowledge_point
    review = candidate.review
    return {
        "index": index,
        "draftId": candidate.draft_id or "",
        "provider": question.provider,
        "passed": review.passed,
        "knowledgeCode": point.knowledge_code,
        "stage": point.stage,
        "primaryDimension": point.primary_dimension,
        "secondaryDimension": point.secondary_dimension,
        "tertiaryAbility": point.tertiary_ability,
        "knowledgePoint": point.knowledge_point,
        "questionType": question.question_type,
        "title": question.title,
        "scenario": question.scenario,
        "question": question.question,
        "options": json.dumps(question.options, ensure_ascii=False),
        "correctAnswer": question.correct_answer,
        "explanation": question.explanation,
        "cognitiveLevel": review.cognitive_level,
        "difficultyEstimate": review.difficulty_estimate,
        "structureResult": review.structure_result,
        "structureIssues": "；".join(review.structure_issues),
        "qualityLevel": review.quality_level,
        "qualityIssues": "；".join(review.quality_issues),
        "duplicateGroup": review.duplicate_group,
        "duplicateScore": review.duplicate_score,
        "duplicateWith": review.duplicate_with,
        "aiReviewProvider": review.ai_review_provider,
        "aiReviewPassed": review.ai_review_passed,
        "aiReviewScore": review.ai_review_score,
        "aiReviewLevel": review.ai_review_level,
        "aiReviewIssues": "；".join(review.ai_review_issues),
        "aiReviewSuggestions": "；".join(review.ai_review_suggestions),
        "tags": "；".join(review.tags),
        "sourceReference": question.source_reference,
    }


def _summary(candidates: List[PipelineCandidate]) -> Dict[str, Any]:
    by_provider: Dict[str, Dict[str, int]] = {}
    by_dimension: Dict[str, Dict[str, int]] = {}
    for candidate in candidates:
        provider = candidate.question.provider
        dimension = candidate.knowledge_point.primary_dimension
        by_provider.setdefault(provider, {"total": 0, "passed": 0, "blocked": 0})
        by_dimension.setdefault(dimension, {"total": 0, "passed": 0, "blocked": 0})
        for bucket in [by_provider[provider], by_dimension[dimension]]:
            bucket["total"] += 1
            bucket["passed" if candidate.review.passed else "blocked"] += 1
    return {"byProvider": by_provider, "byDimension": by_dimension}


def write_report(report: PipelineReport) -> PipelineReport:
    output_dir = Path(report.task.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = _safe_timestamp()
    base_name = f"question_pipeline_{stamp}"
    json_path = output_dir / f"{base_name}.json"
    csv_path = output_dir / f"{base_name}.csv"

    rows = [candidate_to_row(index, candidate) for index, candidate in enumerate(report.candidates, start=1)]
    payload = {
        "task": task_to_dict(report.task),
        "createdDrafts": report.created_drafts,
        "errors": report.errors,
        "selectedKnowledgePoints": [asdict(point) for point in report.selected_points],
        "summary": _summary(report.candidates),
        "candidates": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = list(rows[0].keys()) if rows else [
        "index",
        "draftId",
        "provider",
        "passed",
        "knowledgeCode",
        "stage",
        "primaryDimension",
        "secondaryDimension",
        "tertiaryAbility",
        "knowledgePoint",
        "questionType",
        "title",
        "scenario",
        "question",
        "options",
        "correctAnswer",
        "explanation",
        "cognitiveLevel",
        "difficultyEstimate",
        "structureResult",
        "structureIssues",
        "qualityLevel",
        "qualityIssues",
        "duplicateGroup",
        "duplicateScore",
        "duplicateWith",
        "aiReviewProvider",
        "aiReviewPassed",
        "aiReviewScore",
        "aiReviewLevel",
        "aiReviewIssues",
        "aiReviewSuggestions",
        "tags",
        "sourceReference",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report.report_json = str(json_path)
    report.report_csv = str(csv_path)
    return report
