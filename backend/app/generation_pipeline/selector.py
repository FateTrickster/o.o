from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from backend.app.repositories import list_knowledge_points

from .types import KnowledgePointContext, TaskSpec


DEFAULT_DIMENSIONS = ["理解AI（Understand）", "应用AI（Apply）", "创造AI（Create）", "AI伦理（Ethics）"]


def _to_context(item) -> KnowledgePointContext:
    return KnowledgePointContext(
        id=item.id,
        knowledge_code=item.knowledgeCode,
        stage=item.stage,
        primary_dimension=item.primaryDimension,
        secondary_dimension=item.secondaryDimension,
        tertiary_ability=item.tertiaryAbility,
        knowledge_point=item.knowledgePoint,
        description=item.description,
        cognitive_level=item.cognitiveLevel,
        source_references=item.sourceReferences,
        tags=item.tags,
        source_sheet=item.sourceSheet,
        source_row=item.sourceRow,
    )


def select_knowledge_points(task: TaskSpec) -> List[KnowledgePointContext]:
    points = [_to_context(item) for item in list_knowledge_points(stage=task.stage)]
    if task.knowledge_codes:
        wanted = set(task.knowledge_codes)
        selected = [point for point in points if point.knowledge_code in wanted]
        selected.sort(key=lambda item: task.knowledge_codes.index(item.knowledge_code))
        return selected[: task.max_knowledge_points or None]

    dimensions = task.dimensions or DEFAULT_DIMENSIONS
    by_dimension: Dict[str, List[KnowledgePointContext]] = defaultdict(list)
    for point in points:
        if point.primary_dimension not in dimensions:
            continue
        if task.secondary_dimensions and point.secondary_dimension not in task.secondary_dimensions:
            continue
        by_dimension[point.primary_dimension].append(point)

    selected: List[KnowledgePointContext] = []
    for dimension in dimensions:
        candidates = sorted(
            by_dimension.get(dimension, []),
            key=lambda item: (item.source_row, item.knowledge_code),
        )
        selected.extend(candidates[: task.limit_per_dimension])

    if task.max_knowledge_points > 0:
        selected = selected[: task.max_knowledge_points]
    return selected
