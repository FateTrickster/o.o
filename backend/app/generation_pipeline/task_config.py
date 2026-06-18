from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .types import TaskSpec


def split_csv(values: Iterable[str]) -> List[str]:
    items: List[str] = []
    for value in values:
        items.extend(part.strip() for part in str(value).split(",") if part.strip())
    return items


def load_task_spec(path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> TaskSpec:
    data: Dict[str, Any] = {}
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    if overrides:
        data.update({key: value for key, value in overrides.items() if value not in (None, [], "")})
    return TaskSpec(
        name=str(data.get("name") or "knowledge-point-generation"),
        stage=str(data.get("stage") or "初中"),
        dimensions=list(data.get("dimensions") or []),
        secondary_dimensions=list(data.get("secondaryDimensions") or data.get("secondary_dimensions") or []),
        knowledge_codes=list(data.get("knowledgeCodes") or data.get("knowledge_codes") or []),
        providers=list(data.get("providers") or ["mock"]),
        question_type=str(data.get("questionType") or data.get("question_type") or "单选"),
        count_per_knowledge_point=int(data.get("countPerKnowledgePoint") or data.get("count_per_knowledge_point") or 1),
        limit_per_dimension=int(data.get("limitPerDimension") or data.get("limit_per_dimension") or 5),
        max_knowledge_points=int(data.get("maxKnowledgePoints") or data.get("max_knowledge_points") or 0),
        difficulty_target=str(data.get("difficultyTarget") or data.get("difficulty_target") or "medium"),
        cognitive_level_target=str(data.get("cognitiveLevelTarget") or data.get("cognitive_level_target") or ""),
        requirement=str(data.get("requirement") or ""),
        similarity_threshold=float(data.get("similarityThreshold") or data.get("similarity_threshold") or 0.82),
        write_drafts=bool(data.get("writeDrafts") or data.get("write_drafts") or False),
        output_dir=str(data.get("outputDir") or data.get("output_dir") or "outputs"),
    )


def task_to_dict(task: TaskSpec) -> Dict[str, Any]:
    return {
        "name": task.name,
        "stage": task.stage,
        "dimensions": task.dimensions,
        "secondaryDimensions": task.secondary_dimensions,
        "knowledgeCodes": task.knowledge_codes,
        "providers": task.providers,
        "questionType": task.question_type,
        "countPerKnowledgePoint": task.count_per_knowledge_point,
        "limitPerDimension": task.limit_per_dimension,
        "maxKnowledgePoints": task.max_knowledge_points,
        "difficultyTarget": task.difficulty_target,
        "cognitiveLevelTarget": task.cognitive_level_target,
        "requirement": task.requirement,
        "similarityThreshold": task.similarity_threshold,
        "writeDrafts": task.write_drafts,
        "outputDir": task.output_dir,
    }
