from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TaskSpec:
    name: str = "knowledge-point-generation"
    stage: str = "初中"
    dimensions: List[str] = field(default_factory=list)
    secondary_dimensions: List[str] = field(default_factory=list)
    target_tags: List[str] = field(default_factory=list)
    knowledge_codes: List[str] = field(default_factory=list)
    providers: List[str] = field(default_factory=lambda: ["mock"])
    question_type: str = "单选"
    count_per_knowledge_point: int = 1
    limit_per_dimension: int = 5
    max_knowledge_points: int = 0
    difficulty_target: str = "medium"
    cognitive_level_target: str = ""
    requirement: str = ""
    prompt_batch_size: int = 5
    similarity_threshold: float = 0.82
    ai_review_enabled: bool = False
    ai_review_provider: str = "kimi"
    ai_review_min_score: int = 75
    write_drafts: bool = False
    output_dir: str = "outputs"


@dataclass
class KnowledgePointContext:
    id: str
    knowledge_code: str
    stage: str
    primary_dimension: str
    secondary_dimension: str
    tertiary_ability: str
    knowledge_point: str
    description: str
    cognitive_level: str = ""
    source_references: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_sheet: str = ""
    source_row: int = 0


@dataclass
class GeneratedQuestion:
    provider: str
    knowledge_code: str
    question_type: str
    title: str
    scenario: str
    question: str
    options: List[Dict[str, str]]
    correct_answer: str
    explanation: str
    dimension: str
    secondary_dimension: str
    tertiary_dimension: str
    quaternary_dimension: str
    cognitive_level: str
    difficulty_estimate: str
    tags: List[str] = field(default_factory=list)
    knowledge_points: List[str] = field(default_factory=list)
    source_reference: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewResult:
    structure_result: str
    structure_issues: List[str]
    quality_level: str
    quality_issues: List[str]
    tags: List[str]
    cognitive_level: str
    difficulty_estimate: str
    duplicate_group: str = ""
    duplicate_score: float = 0.0
    duplicate_with: str = ""
    ai_review_provider: str = ""
    ai_review_passed: bool = True
    ai_review_score: int = 0
    ai_review_level: str = ""
    ai_review_issues: List[str] = field(default_factory=list)
    ai_review_suggestions: List[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class PipelineCandidate:
    question: GeneratedQuestion
    knowledge_point: KnowledgePointContext
    review: ReviewResult
    draft_id: Optional[str] = None


@dataclass
class PipelineReport:
    task: TaskSpec
    selected_points: List[KnowledgePointContext]
    candidates: List[PipelineCandidate]
    created_drafts: int = 0
    errors: List[str] = field(default_factory=list)
    report_json: str = ""
    report_csv: str = ""
