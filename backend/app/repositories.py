from pathlib import Path
from typing import Dict, List, Optional
import json
import uuid

from .database import connect, from_json, now_iso, to_json
from .framework import UACE_FRAMEWORK, normalize_framework_selection
from .schemas import (
    GenerationBatch,
    GenerationJob,
    KnowledgeEntry,
    KnowledgeInput,
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


def _row_to_generation_job(row: Dict) -> GenerationJob:
    return GenerationJob(
        id=row["id"],
        provider=row["provider"],
        model=row["model"],
        requirement=row["requirement"] or "",
        targetDimensions=from_json(row["target_dimensions_json"], []),
        targetSecondaryDimensions=from_json(row["target_secondary_dimensions_json"], []),
        targetTags=from_json(row["target_tags_json"], []),
        count=row["count"],
        status=row["status"],
        createdAt=row["created_at"],
        completedAt=row["completed_at"],
        error=row["error"],
        draftCount=row["draft_count"] if "draft_count" in row else 0,
        batchCount=row["batch_count"] if "batch_count" in row else 0,
        completedBatchCount=row["completed_batch_count"] if "completed_batch_count" in row else 0,
        failedBatchCount=row["failed_batch_count"] if "failed_batch_count" in row else 0,
    )


def _row_to_generation_batch(row: Dict) -> GenerationBatch:
    return GenerationBatch(
        id=row["id"],
        jobId=row["job_id"],
        batchIndex=row["batch_index"],
        provider=row["provider"],
        model=row["model"],
        plannedCount=row["planned_count"],
        generatedCount=row["generated_count"],
        status=row["status"],
        startedAt=row["started_at"],
        completedAt=row["completed_at"],
        error=row["error"],
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


def _insert_or_replace_knowledge(connection, entry: KnowledgeEntry) -> None:
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


def upsert_knowledge(entry: KnowledgeEntry) -> None:
    with connect() as connection:
        _insert_or_replace_knowledge(connection, entry)


def create_knowledge(input_data: KnowledgeInput) -> KnowledgeEntry:
    now = now_iso()
    entry = KnowledgeEntry(
        **input_data.dict(),
        id=str(uuid.uuid4()),
        createdAt=now,
        updatedAt=now,
    )
    with connect() as connection:
        _insert_or_replace_knowledge(connection, entry)
    return entry


def create_knowledge_many(inputs: List[KnowledgeInput]) -> Dict[str, int]:
    now = now_iso()
    created = [
        KnowledgeEntry(
            **input_data.dict(),
            id=str(uuid.uuid4()),
            createdAt=now,
            updatedAt=now,
        )
        for input_data in inputs
    ]
    with connect() as connection:
        for entry in created:
            _insert_or_replace_knowledge(connection, entry)
        total = connection.execute("SELECT COUNT(*) AS count FROM knowledge_entries").fetchone()["count"]
    return {"imported": len(created), "total": total}


def update_knowledge(entry_id: str, input_data: KnowledgeInput) -> Optional[KnowledgeEntry]:
    current = get_knowledge(entry_id)
    if not current:
        return None

    entry = KnowledgeEntry(
        **input_data.dict(),
        id=entry_id,
        createdAt=current.createdAt,
        updatedAt=now_iso(),
    )
    with connect() as connection:
        _insert_or_replace_knowledge(connection, entry)
    return entry


def delete_knowledge(entry_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM knowledge_entries WHERE id = ?", (entry_id,))
        return cursor.rowcount > 0


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


def create_generation_batch(
    job_id: str,
    batch_index: int,
    provider: str,
    model: str,
    planned_count: int,
) -> GenerationBatch:
    batch = GenerationBatch(
        id=str(uuid.uuid4()),
        jobId=job_id,
        batchIndex=batch_index,
        provider=provider,
        model=model,
        plannedCount=planned_count,
        generatedCount=0,
        status="running",
        startedAt=now_iso(),
    )
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO generation_batches
            (id, job_id, batch_index, provider, model, planned_count,
             generated_count, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch.id,
                batch.jobId,
                batch.batchIndex,
                batch.provider,
                batch.model,
                batch.plannedCount,
                batch.generatedCount,
                batch.status,
                batch.startedAt,
            ),
        )
    return batch


def complete_generation_batch(
    batch_id: str,
    status: str,
    generated_count: int = 0,
    error: Optional[str] = None,
) -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE generation_batches
            SET status = ?, generated_count = ?, completed_at = ?, error = ?
            WHERE id = ?
            """,
            (status, generated_count, now_iso(), error, batch_id),
        )


def list_generation_batches(job_id: Optional[str] = None) -> List[GenerationBatch]:
    query = "SELECT * FROM generation_batches"
    params: List[str] = []
    if job_id:
        query += " WHERE job_id = ?"
        params.append(job_id)
    query += " ORDER BY started_at DESC, batch_index DESC LIMIT 200"
    with connect() as connection:
        rows = connection.execute(query, params).fetchall()
        return [_row_to_generation_batch(dict(row)) for row in rows]


def list_generation_jobs() -> List[GenerationJob]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT generation_jobs.*,
                   COUNT(DISTINCT question_drafts.id) AS draft_count,
                   COUNT(DISTINCT generation_batches.id) AS batch_count,
                   COUNT(DISTINCT CASE WHEN generation_batches.status = 'completed' THEN generation_batches.id END)
                     AS completed_batch_count,
                   COUNT(DISTINCT CASE WHEN generation_batches.status = 'failed' THEN generation_batches.id END)
                     AS failed_batch_count
            FROM generation_jobs
            LEFT JOIN question_drafts
              ON question_drafts.generation_job_id = generation_jobs.id
            LEFT JOIN generation_batches
              ON generation_batches.job_id = generation_jobs.id
            GROUP BY generation_jobs.id
            ORDER BY generation_jobs.created_at DESC
            LIMIT 50
            """
        ).fetchall()
        return [_row_to_generation_job(dict(row)) for row in rows]


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


def _insert_or_replace_draft(connection, draft: QuestionDraft) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO question_drafts
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


def _insert_or_replace_question(connection, question: Question) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO questions
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


def update_draft(draft_id: str, input_data: QuestionInput) -> Optional[QuestionDraft]:
    current = get_draft(draft_id)
    if not current:
        return None

    selection = normalize_framework_selection(
        input_data.dimension,
        input_data.secondaryDimension,
        f"{input_data.title} {input_data.question} {input_data.scenario} {input_data.subSkill} {' '.join(input_data.tags)}",
    )
    updated = QuestionDraft(
        **input_data.dict(exclude={"dimension", "secondaryDimension"}),
        dimension=selection["dimension"],
        secondaryDimension=selection["secondaryDimension"],
        id=draft_id,
        sourceKnowledgeIds=current.sourceKnowledgeIds,
        generationRequirement=current.generationRequirement,
        generationJobId=current.generationJobId,
        createdAt=current.createdAt,
        updatedAt=now_iso(),
    )
    with connect() as connection:
        _insert_or_replace_draft(connection, updated)
    return updated


def delete_draft(draft_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM question_drafts WHERE id = ?", (draft_id,))
        return cursor.rowcount > 0


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
        _insert_or_replace_question(connection, question)
        connection.execute("DELETE FROM question_drafts WHERE id = ?", (draft_id,))
    return question


def create_question(input_data: QuestionInput) -> Question:
    selection = normalize_framework_selection(
        input_data.dimension,
        input_data.secondaryDimension,
        f"{input_data.title} {input_data.question} {input_data.scenario} {input_data.subSkill} {' '.join(input_data.tags)}",
    )
    now = now_iso()
    with connect() as connection:
        question = Question(
            **input_data.dict(exclude={"dimension", "secondaryDimension"}),
            dimension=selection["dimension"],
            secondaryDimension=selection["secondaryDimension"],
            id=str(uuid.uuid4()),
            itemCode=_next_item_code(connection),
            createdAt=now,
            updatedAt=now,
        )
        _insert_or_replace_question(connection, question)
    return question


def list_questions() -> List[Question]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM questions ORDER BY item_code ASC"
        ).fetchall()
        return [_row_to_question(dict(row)) for row in rows]


def filter_questions(
    dimension: Optional[str] = None,
    secondary_dimension: Optional[str] = None,
    status: Optional[str] = None,
    difficulty: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Question]:
    questions = list_questions()
    normalized_tag = tag.strip().lower() if tag else ""
    normalized_search = search.strip().lower() if search else ""
    filtered: List[Question] = []

    for question in questions:
        if dimension and question.dimension != dimension:
            continue
        if secondary_dimension and question.secondaryDimension != secondary_dimension:
            continue
        if status and question.status != status:
            continue
        if difficulty and question.difficultyEstimate != difficulty:
            continue
        if normalized_tag and not any(normalized_tag in item.lower() for item in question.tags):
            continue
        if normalized_search:
            haystack = " ".join(
                [
                    question.itemCode,
                    question.title,
                    question.question,
                    question.scenario,
                    question.dimension,
                    question.secondaryDimension,
                    question.subSkill,
                    " ".join(question.tags),
                ]
            ).lower()
            if normalized_search not in haystack:
                continue
        filtered.append(question)

    return filtered


def get_question(question_id: str) -> Optional[Question]:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM questions WHERE id = ?", (question_id,)
        ).fetchone()
        return _row_to_question(dict(row)) if row else None


def update_question(question_id: str, input_data: QuestionInput) -> Optional[Question]:
    current = get_question(question_id)
    if not current:
        return None

    selection = normalize_framework_selection(
        input_data.dimension,
        input_data.secondaryDimension,
        f"{input_data.title} {input_data.question} {input_data.scenario} {input_data.subSkill} {' '.join(input_data.tags)}",
    )
    updated = Question(
        **input_data.dict(exclude={"dimension", "secondaryDimension"}),
        dimension=selection["dimension"],
        secondaryDimension=selection["secondaryDimension"],
        id=question_id,
        itemCode=current.itemCode,
        createdAt=current.createdAt,
        updatedAt=now_iso(),
    )
    with connect() as connection:
        _insert_or_replace_question(connection, updated)
    return updated


def delete_question(question_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        return cursor.rowcount > 0


def _is_valid_item_code(value: Optional[str]) -> bool:
    return bool(value and len(value) == 5 and value.isdigit())


def import_questions(imported: List[Dict]) -> Dict[str, int]:
    with connect() as connection:
        for raw in imported:
            incoming_id = raw.get("id") or str(uuid.uuid4())
            current = connection.execute(
                "SELECT * FROM questions WHERE id = ?", (incoming_id,)
            ).fetchone()
            incoming_code = raw.get("itemCode")
            item_code = incoming_code if _is_valid_item_code(incoming_code) else None

            if item_code:
                conflict = connection.execute(
                    "SELECT id FROM questions WHERE item_code = ? AND id != ?",
                    (item_code, incoming_id),
                ).fetchone()
                if conflict:
                    item_code = None

            if not item_code and current:
                item_code = current["item_code"]
            if not item_code:
                item_code = _next_item_code(connection)

            question = _question_from_raw({**raw, "id": incoming_id, "itemCode": item_code}, item_code)
            _insert_or_replace_question(connection, question)

        total = connection.execute("SELECT COUNT(*) AS count FROM questions").fetchone()["count"]

    return {"imported": len(imported), "total": total}


def _question_input_from_raw(raw: Dict) -> QuestionInput:
    tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
    selection = normalize_framework_selection(
        raw.get("dimension", ""),
        raw.get("secondaryDimension", ""),
        f"{raw.get('title', '')} {raw.get('question', '')} {raw.get('scenario', '')} {raw.get('subSkill', '')} {' '.join(tags)}",
    )
    return QuestionInput(
        title=raw.get("title", ""),
        question=raw.get("question", ""),
        scenario=raw.get("scenario", ""),
        options=raw.get("options") or [],
        correctAnswer=raw.get("correctAnswer", ""),
        explanation=raw.get("explanation", ""),
        dimension=selection["dimension"],
        secondaryDimension=selection["secondaryDimension"],
        subSkill=raw.get("subSkill") or selection["secondaryDimension"],
        cognitiveLevel=raw.get("cognitiveLevel", "apply"),
        difficultyEstimate=raw.get("difficultyEstimate", "medium"),
        tags=tags,
        sourceReference=raw.get("sourceReference", ""),
        status=raw.get("status", "draft"),
    )


def _draft_from_raw(raw: Dict) -> QuestionDraft:
    input_data = _question_input_from_raw(raw)
    now = now_iso()
    return QuestionDraft(
        **input_data.dict(),
        id=raw.get("id") or str(uuid.uuid4()),
        sourceKnowledgeIds=raw.get("sourceKnowledgeIds") or [],
        generationRequirement=raw.get("generationRequirement", ""),
        generationJobId=raw.get("generationJobId"),
        createdAt=raw.get("createdAt") or now,
        updatedAt=raw.get("updatedAt") or now,
    )


def _question_from_raw(raw: Dict, fallback_item_code: str) -> Question:
    input_data = _question_input_from_raw(raw)
    now = now_iso()
    item_code = raw.get("itemCode") or fallback_item_code
    return Question(
        **input_data.dict(),
        id=raw.get("id") or str(uuid.uuid4()),
        itemCode=item_code,
        createdAt=raw.get("createdAt") or now,
        updatedAt=raw.get("updatedAt") or now,
    )


def import_json_data(root_data_dir: Path) -> Dict[str, int]:
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

    with connect() as connection:
        questions_file = root_data_dir / "questions.json"
        if questions_file.exists():
            used_codes = {
                row["item_code"]
                for row in connection.execute("SELECT item_code FROM questions").fetchall()
            }
            for raw in json.loads(questions_file.read_text(encoding="utf-8")):
                fallback_code = _next_item_code(connection)
                question = _question_from_raw(raw, fallback_code)
                if question.itemCode in used_codes and not raw.get("itemCode"):
                    question.itemCode = _next_item_code(connection)
                used_codes.add(question.itemCode)
                _insert_or_replace_question(connection, question)
                counts["questions"] += 1

        drafts_file = root_data_dir / "drafts.json"
        if drafts_file.exists():
            for raw in json.loads(drafts_file.read_text(encoding="utf-8")):
                _insert_or_replace_draft(connection, _draft_from_raw(raw))
                counts["drafts"] += 1

    return counts
