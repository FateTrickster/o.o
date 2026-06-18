from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from backend.app.config import get_db_path
from backend.app.database import init_db
from backend.app.repositories import (
    complete_generation_batch,
    complete_generation_job,
    create_drafts,
    create_generation_batch,
    create_generation_job,
    list_drafts,
    list_knowledge,
    list_questions,
    seed_framework,
)
from backend.app.schemas import KnowledgeEntry, QuestionInput, QuestionOption


DEFAULT_OUTPUT = Path("data/codex_generation_plan.json")


def _split_csv(values: Sequence[str]) -> List[str]:
    items: List[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(",") if part.strip())
    return items


def _matches_any_tag(entry: KnowledgeEntry, tags: Sequence[str]) -> bool:
    if not tags:
        return True
    entry_tags = {tag.strip().lower() for tag in entry.tags}
    return any(tag.strip().lower() in entry_tags for tag in tags)


def _select_knowledge(
    entries: Iterable[KnowledgeEntry],
    knowledge_ids: Sequence[str],
    tags: Sequence[str],
    max_knowledge: int,
) -> List[KnowledgeEntry]:
    selected = list(entries)
    if knowledge_ids:
        wanted = set(knowledge_ids)
        selected = [entry for entry in selected if entry.id in wanted]
    if tags:
        selected = [entry for entry in selected if _matches_any_tag(entry, tags)]
    if max_knowledge > 0:
        selected = selected[:max_knowledge]
    return selected


def _trim_content(content: str, max_chars: int) -> str:
    normalized = re.sub(r"\s+", " ", content).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def _plan_payload(args: argparse.Namespace, entries: Sequence[KnowledgeEntry], tags: Sequence[str]) -> Dict[str, Any]:
    target_dimensions = [args.dimension] if args.dimension else []
    target_secondary_dimensions = [args.secondary_dimension] if args.secondary_dimension else []
    return {
        "mode": "codex-assisted-draft-generation",
        "database": str(get_db_path()),
        "instructions": [
            "Generate question drafts from each item in knowledgeItems.",
            "Return JSON only. Do not include Markdown.",
            "Use the exact output schema shown in outputSchema.",
            "Each generated question must cite the source knowledge by setting sourceKnowledgeIds to the item's id.",
            "Write scenario-based AI literacy questions, not generic memorization questions.",
            "Generated questions should be reviewed before being accepted into the formal question bank.",
        ],
        "generationDefaults": {
            "perKnowledge": args.per_knowledge,
            "targetDimensions": target_dimensions,
            "targetSecondaryDimensions": target_secondary_dimensions,
            "targetTags": list(tags),
            "requirement": args.requirement,
        },
        "outputSchema": {
            "items": [
                {
                    "knowledgeId": "knowledge entry id",
                    "questions": [
                        {
                            "questionType": "单选",
                            "title": "short title",
                            "question": "question stem",
                            "scenario": "realistic scenario",
                            "options": [
                                {"id": "A", "text": "option text"},
                                {"id": "B", "text": "option text"},
                                {"id": "C", "text": "option text"},
                                {"id": "D", "text": "option text"},
                            ],
                            "correctAnswer": "A",
                            "explanation": "explain why the answer is best",
                            "dimension": "一级维度",
                            "secondaryDimension": "二级维度",
                            "tertiaryDimension": "三级维度，可空",
                            "quaternaryDimension": "四级维度，可空",
                            "subSkill": "考查能力",
                            "cognitiveLevel": "remember/understand/apply/analyze/evaluate/create",
                            "difficultyEstimate": "easy/medium/hard",
                            "tags": ["tag"],
                            "knowledgePoints": ["reference knowledge point"],
                            "sourceReference": "source title or chunk",
                            "status": "draft",
                        }
                    ],
                }
            ]
        },
        "knowledgeItems": [
            {
                "id": entry.id,
                "title": entry.title,
                "sourceFileName": entry.sourceFileName,
                "sourceType": entry.sourceType,
                "tags": entry.tags,
                "content": _trim_content(entry.content, args.max_chars),
                "draftCount": args.per_knowledge,
            }
            for entry in entries
        ],
    }


def write_plan(args: argparse.Namespace) -> int:
    init_db()
    seed_framework()
    tags = _split_csv(args.tag)
    knowledge_ids = _split_csv(args.knowledge_id)
    entries = _select_knowledge(list_knowledge(), knowledge_ids, tags, args.max_knowledge)
    payload = _plan_payload(args, entries, tags)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote plan: {output_path}")
    print(f"Knowledge entries: {len(entries)}")
    print(f"Planned drafts: {sum(item['draftCount'] for item in payload['knowledgeItems'])}")
    return 0 if entries else 1


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _dedupe_key(raw: Dict[str, Any]) -> str:
    return _normalize_text(" ".join([str(raw.get("title", "")), str(raw.get("question", ""))]))


def _existing_keys() -> set[str]:
    keys: set[str] = set()
    for question in list_questions():
        keys.add(_normalize_text(f"{question.title} {question.question}"))
    for draft in list_drafts():
        keys.add(_normalize_text(f"{draft.title} {draft.question}"))
    return keys


def _normalize_options(raw_options: Any) -> List[QuestionOption]:
    if isinstance(raw_options, dict):
        return [
            QuestionOption(id=str(key).strip(), text=str(value).strip())
            for key, value in raw_options.items()
            if str(key).strip() and str(value).strip()
        ]

    if isinstance(raw_options, list):
        options: List[QuestionOption] = []
        for index, option in enumerate(raw_options):
            default_id = chr(65 + index)
            if isinstance(option, dict):
                option_id = str(option.get("id") or option.get("key") or option.get("label") or default_id).strip()
                text = str(option.get("text") or option.get("content") or option.get("value") or "").strip()
            else:
                option_id = default_id
                text = str(option).strip()
            if option_id and text:
                options.append(QuestionOption(id=option_id, text=text))
        return options

    return []


def _normalize_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,，、;；\n]", value) if item.strip()]
    return []


def _normalize_answer(value: Any) -> str:
    if isinstance(value, list):
        return "".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _question_from_raw(raw: Dict[str, Any]) -> QuestionInput:
    return QuestionInput(
        questionType=str(raw.get("questionType", "单选")).strip() or "单选",
        title=str(raw.get("title", "")).strip(),
        question=str(raw.get("question", "")).strip(),
        scenario=str(raw.get("scenario", "")).strip(),
        options=_normalize_options(raw.get("options")),
        correctAnswer=_normalize_answer(raw.get("correctAnswer")),
        explanation=str(raw.get("explanation", "")).strip(),
        dimension=str(raw.get("dimension", "")).strip(),
        secondaryDimension=str(raw.get("secondaryDimension", "")).strip(),
        tertiaryDimension=str(raw.get("tertiaryDimension", "")).strip(),
        quaternaryDimension=str(raw.get("quaternaryDimension", "")).strip(),
        subSkill=str(raw.get("subSkill", "")).strip(),
        cognitiveLevel=str(raw.get("cognitiveLevel", "apply")).strip() or "apply",
        difficultyEstimate=str(raw.get("difficultyEstimate", "medium")).strip() or "medium",
        tags=_normalize_string_list(raw.get("tags")),
        knowledgePoints=_normalize_string_list(raw.get("knowledgePoints")),
        sourceReference=str(raw.get("sourceReference", "")).strip(),
        status=str(raw.get("status", "draft")).strip() or "draft",
    )


def _load_generated_items(path: Path) -> List[Tuple[List[str], List[Dict[str, Any]]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [([], payload)]
    if not isinstance(payload, dict):
        raise ValueError("Generated draft file must contain a JSON object or array")

    if isinstance(payload.get("items"), list):
        items: List[Tuple[List[str], List[Dict[str, Any]]]] = []
        for item in payload["items"]:
            if not isinstance(item, dict):
                continue
            knowledge_id = str(item.get("knowledgeId", "")).strip()
            questions = item.get("questions")
            if isinstance(questions, list):
                items.append(([knowledge_id] if knowledge_id else [], questions))
        return items

    if isinstance(payload.get("questions"), list):
        knowledge_ids = _normalize_string_list(payload.get("sourceKnowledgeIds"))
        return [(knowledge_ids, payload["questions"])]

    raise ValueError("Generated draft file must include items[].questions or questions")


def import_generated(args: argparse.Namespace) -> int:
    init_db()
    seed_framework()
    input_path = Path(args.input)
    generated_items = _load_generated_items(input_path)
    existing = _existing_keys()
    skipped_duplicates = 0
    skipped_invalid = 0
    created_total = 0
    failures: List[str] = []
    requirement = args.requirement or f"Codex assisted import from {input_path}"

    planned_total = sum(len(raw_questions) for _, raw_questions in generated_items)
    job = None
    if not args.dry_run:
        job = create_generation_job(
            provider="codex",
            model=args.model,
            requirement=requirement,
            target_dimensions=[],
            target_secondary_dimensions=[],
            target_tags=[],
            count=planned_total,
        )

    for index, (knowledge_ids, raw_questions) in enumerate(generated_items, start=1):
        batch = None
        if job:
            batch = create_generation_batch(
                job_id=job.id,
                batch_index=index,
                provider="codex",
                model=args.model,
                planned_count=len(raw_questions),
            )
        questions: List[QuestionInput] = []
        for raw in raw_questions:
            if not isinstance(raw, dict):
                skipped_invalid += 1
                continue
            key = _dedupe_key(raw)
            if key in existing and not args.allow_duplicates:
                skipped_duplicates += 1
                continue
            try:
                question = _question_from_raw(raw)
            except Exception as exc:
                skipped_invalid += 1
                failures.append(f"Invalid question in batch {index}: {exc}")
                continue
            questions.append(question)
            existing.add(key)

        if args.dry_run:
            print(f"[dry-run] batch {index}: valid={len(questions)} skipped_duplicates={skipped_duplicates}")
            continue

        try:
            drafts = create_drafts(
                questions=questions,
                source_knowledge_ids=knowledge_ids,
                generation_requirement=requirement,
                generation_job_id=job.id,
            )
        except Exception as exc:
            failures.append(f"Batch {index}: {exc}")
            if batch:
                complete_generation_batch(batch.id, "failed", 0, str(exc))
            if args.stop_on_error:
                break
            continue

        created_total += len(drafts)
        if batch:
            complete_generation_batch(batch.id, "completed", len(drafts))
        print(f"batch {index}: created={len(drafts)} sourceKnowledgeIds={knowledge_ids or '-'}")

    status = "completed" if not failures else ("partial" if created_total else "failed")
    if job:
        complete_generation_job(job.id, status, "\n".join(failures) if failures else None)

    print("")
    print("Import finished")
    print(f"- job id: {job.id if job else '-'}")
    print(f"- planned questions: {planned_total}")
    print(f"- created drafts: {created_total}")
    print(f"- skipped duplicates: {skipped_duplicates}")
    print(f"- skipped invalid: {skipped_invalid}")
    if failures:
        print("- failures:")
        for failure in failures[:10]:
            print(f"  - {failure}", file=sys.stderr)
    return 1 if failures and not created_total else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and import Codex-assisted question drafts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Export a knowledge-backed generation plan for Codex.")
    plan.add_argument("--per-knowledge", type=int, default=2, help="Drafts to generate per knowledge entry.")
    plan.add_argument("--max-knowledge", type=int, default=3, help="Maximum knowledge entries. Use 0 for no limit.")
    plan.add_argument("--knowledge-id", action="append", default=[], help="Specific knowledge id. Can be repeated.")
    plan.add_argument("--tag", action="append", default=[], help="Filter/target tag. Can be repeated or comma-separated.")
    plan.add_argument("--dimension", default="", help="Target primary dimension.")
    plan.add_argument("--secondary-dimension", default="", help="Target secondary dimension.")
    plan.add_argument("--requirement", default="", help="Additional generation requirement.")
    plan.add_argument("--max-chars", type=int, default=1800, help="Maximum characters per knowledge chunk in the plan.")
    plan.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON plan path.")
    plan.set_defaults(func=write_plan)

    importer = subparsers.add_parser("import", help="Validate and import Codex-generated drafts into SQLite.")
    importer.add_argument("--input", required=True, help="Generated JSON file to import.")
    importer.add_argument("--model", default="codex-session", help="Generation model/session label for audit records.")
    importer.add_argument("--requirement", default="", help="Requirement text stored on generated drafts.")
    importer.add_argument("--allow-duplicates", action="store_true", help="Do not skip title/stem duplicates.")
    importer.add_argument("--stop-on-error", action="store_true", help="Stop importing after the first failed batch.")
    importer.add_argument("--dry-run", action="store_true", help="Validate and report without creating drafts.")
    importer.set_defaults(func=import_generated)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
