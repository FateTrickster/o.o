from typing import Dict, List, Optional
import json
import uuid

from .database import connect, from_json, now_iso, to_json
from .framework import UACE_FRAMEWORK, normalize_framework_selection
from .schemas import (
    GenerationJob,
    KnowledgeEntry,
    Question,
    QuestionDraft,
    QuestionInput,
)


def _row_to_knowledge(row: Dict) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        sourceFileName=row["source_file_name"] or "",
        sourceType=row["source_type"] or "",
        tags=from_json(row["tags_json"], []),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _row_to_draft(row: Dict) -> QuestionDraft:
    return QuestionDraft(
        id=row["id"],
        title=row["title"],
        question=row["question"],
        scenario=row["scenario"],
        options=from_json(row["options_json"], []),
        correctAnswer=row["correct_answer"],
        explanation=row["explanation"],
        dimension=row["dimension"],
        secondaryDimension=row["secondary_dimension"],
        subSkill=row["sub_skill"],
        cognitiveLevel=row["cognitive_level"],
        difficultyEstimate=row["difficulty_estimate"],
        tags=from_json(row["tags_json"], []),
        sourceReference=row["source_reference"] or "",
        status=row["status"],
        sourceKnowledgeIds=from_json(row["source_knowledge_ids_json"], []),
        generationRequirement=row["generation_requirement"] or "",
        generationJobId=row["generation_job_id"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _row_to_question(row: Dict) -> Question:
    return Question(
        id=row["id"],
        itemCode=row["item_code"],
        title=row["title"],
        question=row["question"],
        scenario=row["scenario"],
        options=from_json(row["options_json"], []),
        correctAnswer=row["correct_answer"],
        explanation=row["explanation"],
        dimension=row["dimension"],
        secondaryDimension=row["secondary_dimension"],
        subSkill=row["sub_skill"],
        cognitiveLevel=row["cognitive_level"],
        difficultyEstimate=row["difficulty_estimate"],
        tags=from_json(row["tags_json"], []),
        sourceReference=row["source_reference"] or "",
        status=row["status"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def seed_framework() -> None:
    with connect() as connection:
        for item in UACE_FRAMEWORK:
            connection.execute(
                """
                INSERT OR REPLACE INTO framework_dimensions (code, dimension)
                VALUES (?, ?)
                """,
                (item["code"], item["dimension"]),
            )
            for index, secondary in enumerate(item["secondaryDimensions"]):
                connection.execute(
                    """
                    INSERT OR REPLACE INTO framework_secondary_dimensions
                    (id, dimension, secondary_dimension, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (f"{item['code']}-{index + 1}", item["dimension"], secondary, index + 1),
                )


def list_knowledge() -> List[KnowledgeEntry]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM knowledge_entries ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_knowledge(dict(row)) for row in rows]


def get_knowledge(entry_id: str) -> Optional[KnowledgeEntry]:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM knowledge_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return _row_to_knowledge(dict(row)) if row else None


def upsert_knowledge(entry: KnowledgeEntry) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO knowledge_entries
            (id, title, content, source_file_name, source_type, tags_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.title,
                entry.content,
                entry.sourceFileName,
                entry.sourceType,
                to_json(entry.tags),
                entry.createdAt,
                entry.updatedAt,
            ),
        )


def create_generation_job(
    provider: str,
    model: str,
    requirement: str,
    target_dimensions: List[str],
    target_secondary_dimensions: List[str],
    target_tags: List[str],
    count: int,
) -> GenerationJob:
    job = GenerationJob(
        id=str(uuid.uuid4()),
        provider=provider,
        model=model,
        requirement=requirement,
        targetDimensions=target_dimensions,
        targetSecondaryDimensions=target_secondary_dimensions,
        targetTags=target_tags,
        count=count,
        status="running",
        createdAt=now_iso(),
    )
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO generation_jobs
            (id, provider, model, requirement, target_dimensions_json,
             target_secondary_dimensions_json, target_tags_json, count, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.provider,
                job.model,
                job.requirement,
                to_json(job.targetDimensions),
                to_json(job.targetSecondaryDimensions),
                to_json(job.targetTags),
                job.count,
                job.status,
                job.createdAt,
            ),
        )
    return job


def complete_generation_job(job_id: str, status: str, error: Optional[str] = None) -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE generation_jobs
            SET status = ?, completed_at = ?, error = ?
            WHERE id = ?
            """,
            (status, now_iso(), error, job_id),
        )


def list_drafts() -> List[QuestionDraft]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM question_drafts ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_draft(dict(row)) for row in rows]


def get_draft(draft_id: str) -> Optional[QuestionDraft]:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM question_drafts WHERE id = ?", (draft_id,)
        ).fetchone()
        return _row_to_draft(dict(row)) if row else None


def create_drafts(
    questions: List[QuestionInput],
    source_knowledge_ids: List[str],
    generation_requirement: str,
    generation_job_id: str,
) -> List[QuestionDraft]:
    now = now_iso()
    drafts: List[QuestionDraft] = []
    with connect() as connection:
        for question in questions:
            selection = normalize_framework_selection(
                question.dimension,
                question.secondaryDimension,
                f"{question.title} {question.question} {question.scenario} {question.subSkill} {' '.join(question.tags)}",
            )
            draft = QuestionDraft(
                **question.dict(exclude={"dimension", "secondaryDimension"}),
                dimension=selection["dimension"],
                secondaryDimension=selection["secondaryDimension"],
                id=str(uuid.uuid4()),
                sourceKnowledgeIds=source_knowledge_ids,
                generationRequirement=generation_requirement,
                generationJobId=generation_job_id,
                createdAt=now,
                updatedAt=now,
            )
            connection.execute(
                """
                INSERT INTO question_drafts
                (id, title, question, scenario, options_json, correct_answer,
                 explanation, dimension, secondary_dimension, sub_skill,
                 cognitive_level, difficulty_estimate, tags_json, source_reference,
                 status, source_knowledge_ids_json, generation_requirement,
                 generation_job_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.id,
                    draft.title,
                    draft.question,
                    draft.scenario,
                    to_json([option.dict() for option in draft.options]),
                    draft.correctAnswer,
                    draft.explanation,
                    draft.dimension,
                    draft.secondaryDimension,
                    draft.subSkill,
                    draft.cognitiveLevel,
                    draft.difficultyEstimate,
                    to_json(draft.tags),
                    draft.sourceReference,
                    draft.status,
                    to_json(draft.sourceKnowledgeIds),
                    draft.generationRequirement,
                    draft.generationJobId,
                    draft.createdAt,
                    draft.updatedAt,
                ),
            )
            drafts.append(draft)
    return drafts


def _next_item_code(connection) -> str:
    rows = connection.execute("SELECT item_code FROM questions").fetchall()
    max_code = 0
    for row in rows:
        value = row["item_code"]
        if value and value.isdigit():
            max_code = max(max_code, int(value))
    return str(max_code + 1).zfill(5)


def accept_draft(draft_id: str) -> Optional[Question]:
    draft = get_draft(draft_id)
    if not draft:
        return None

    now = now_iso()
    with connect() as connection:
        item_code = _next_item_code(connection)
        question = Question(
            **draft.dict(
                exclude={
                    "id",
                    "sourceKnowledgeIds",
                    "generationRequirement",
                    "generationJobId",
                    "createdAt",
                    "updatedAt",
                }
            ),
            id=str(uuid.uuid4()),
            itemCode=item_code,
            createdAt=now,
            updatedAt=now,
        )
        connection.execute(
            """
            INSERT INTO questions
            (id, item_code, title, question, scenario, options_json,
             correct_answer, explanation, dimension, secondary_dimension,
             sub_skill, cognitive_level, difficulty_estimate, tags_json,
             source_reference, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question.id,
                question.itemCode,
                question.title,
                question.question,
                question.scenario,
                to_json([option.dict() for option in question.options]),
                question.correctAnswer,
                question.explanation,
                question.dimension,
                question.secondaryDimension,
                question.subSkill,
                question.cognitiveLevel,
                question.difficultyEstimate,
                to_json(question.tags),
                question.sourceReference,
                question.status,
                question.createdAt,
                question.updatedAt,
            ),
        )
        connection.execute("DELETE FROM question_drafts WHERE id = ?", (draft_id,))
    return question


def list_questions() -> List[Question]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM questions ORDER BY item_code ASC"
        ).fetchall()
        return [_row_to_question(dict(row)) for row in rows]


def import_json_data(root_data_dir) -> Dict[str, int]:
    counts = {"knowledge": 0, "drafts": 0, "questions": 0}

    knowledge_file = root_data_dir / "knowledge.json"
    if knowledge_file.exists():
        for raw in json.loads(knowledge_file.read_text(encoding="utf-8")):
            upsert_knowledge(
                KnowledgeEntry(
                    id=raw.get("id") or str(uuid.uuid4()),
                    title=raw.get("title", ""),
                    content=raw.get("content", ""),
                    sourceFileName=raw.get("sourceFileName", ""),
                    sourceType=raw.get("sourceType", ""),
                    tags=raw.get("tags") or [],
                    createdAt=raw.get("createdAt") or now_iso(),
                    updatedAt=raw.get("updatedAt") or now_iso(),
                )
            )
            counts["knowledge"] += 1

    # Existing questions/drafts are intentionally not fully imported yet; the MVP
    # backend focuses on new Python-generated drafts while keeping Next.js data intact.
    return counts
