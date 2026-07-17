from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .types import TaskSpec


def _list_value(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return split_csv([value])
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def split_csv(values: Iterable[str]) -> List[str]:
    items: List[str] = []
    for value in values:
        items.extend(part.strip() for part in str(value).split(",") if part.strip())
    return items


def _bool_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_task_spec(path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> TaskSpec:
    data: Dict[str, Any] = {}
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    if overrides:
        data.update({key: value for key, value in overrides.items() if value not in (None, [], "")})
    return TaskSpec(
        name=str(data.get("name") or "knowledge-point-generation"),
        stage=str(data.get("stage") or "初中"),
        dimensions=_list_value(data.get("dimensions")),
        secondary_dimensions=_list_value(data.get("secondaryDimensions") or data.get("secondary_dimensions")),
        target_tags=_list_value(data.get("targetTags") or data.get("target_tags")),
        knowledge_codes=_list_value(data.get("knowledgeCodes") or data.get("knowledge_codes")),
        providers=_list_value(data.get("providers")) or ["mock"],
        question_type=str(data.get("questionType") or data.get("question_type") or "单选"),
        count_per_knowledge_point=int(data.get("countPerKnowledgePoint") or data.get("count_per_knowledge_point") or 1),
        limit_per_dimension=int(data.get("limitPerDimension") or data.get("limit_per_dimension") or 5),
        max_knowledge_points=int(data.get("maxKnowledgePoints") or data.get("max_knowledge_points") or 0),
        difficulty_target=str(data.get("difficultyTarget") or data.get("difficulty_target") or "medium"),
        cognitive_level_target=str(data.get("cognitiveLevelTarget") or data.get("cognitive_level_target") or ""),
        requirement=str(data.get("requirement") or ""),
        prompt_batch_size=int(data.get("promptBatchSize") or data.get("prompt_batch_size") or 5),
        similarity_threshold=float(data.get("similarityThreshold") or data.get("similarity_threshold") or 0.82),
        ai_review_enabled=_bool_value(data.get("aiReviewEnabled") or data.get("ai_review_enabled"), False),
        ai_review_provider=str(data.get("aiReviewProvider") or data.get("ai_review_provider") or "kimi"),
        ai_review_min_score=int(data.get("aiReviewMinScore") or data.get("ai_review_min_score") or 75),
        write_drafts=_bool_value(data.get("writeDrafts") or data.get("write_drafts"), False),
        output_dir=str(data.get("outputDir") or data.get("output_dir") or "outputs"),
        use_rag=_bool_value(data.get("useRag") or data.get("use_rag"), False),
        rag_top_k=int(data.get("ragTopK") or data.get("rag_top_k") or 3),
    )


def task_to_dict(task: TaskSpec) -> Dict[str, Any]:
    return {
        "name": task.name,
        "stage": task.stage,
        "dimensions": task.dimensions,
        "secondaryDimensions": task.secondary_dimensions,
        "targetTags": task.target_tags,
        "knowledgeCodes": task.knowledge_codes,
        "providers": task.providers,
        "questionType": task.question_type,
        "countPerKnowledgePoint": task.count_per_knowledge_point,
        "limitPerDimension": task.limit_per_dimension,
        "maxKnowledgePoints": task.max_knowledge_points,
        "difficultyTarget": task.difficulty_target,
        "cognitiveLevelTarget": task.cognitive_level_target,
        "requirement": task.requirement,
        "promptBatchSize": task.prompt_batch_size,
        "similarityThreshold": task.similarity_threshold,
        "aiReviewEnabled": task.ai_review_enabled,
        "aiReviewProvider": task.ai_review_provider,
        "aiReviewMinScore": task.ai_review_min_score,
        "writeDrafts": task.write_drafts,
        "outputDir": task.output_dir,
        "useRag": task.use_rag,
        "ragTopK": task.rag_top_k,
    }
