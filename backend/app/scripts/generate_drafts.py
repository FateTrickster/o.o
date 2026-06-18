from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from backend.app.config import get_deepseek_model, get_xfyun_model
from backend.app.database import init_db
from backend.app.pipeline import generate_drafts
from backend.app.repositories import list_knowledge, seed_framework
from backend.app.schemas import GenerateDraftRequest, KnowledgeEntry


@dataclass
class GenerationPlanItem:
    index: int
    knowledge: KnowledgeEntry
    count: int


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


def _build_plan(entries: Sequence[KnowledgeEntry], per_knowledge: int) -> List[GenerationPlanItem]:
    return [
        GenerationPlanItem(index=index, knowledge=entry, count=per_knowledge)
        for index, entry in enumerate(entries, start=1)
    ]


def _format_tags(tags: Sequence[str]) -> str:
    return ", ".join(tags) if tags else "-"


def _default_model(provider: str) -> str:
    if provider == "deepseek":
        return get_deepseek_model()
    return get_xfyun_model()


def print_plan(plan: Sequence[GenerationPlanItem], args: argparse.Namespace, target_tags: Sequence[str]) -> None:
    total = sum(item.count for item in plan)
    print("Generation plan")
    print(f"- provider: {args.provider}")
    print(f"- model: {args.model or _default_model(args.provider)}")
    print(f"- per knowledge: {args.per_knowledge}")
    print(f"- knowledge entries: {len(plan)}")
    print(f"- planned drafts: {total}")
    print(f"- dimension: {args.dimension or '-'}")
    print(f"- secondary dimension: {args.secondary_dimension or '-'}")
    print(f"- target/filter tags: {_format_tags(target_tags)}")
    print(f"- requirement: {args.requirement or '-'}")
    print("")
    for item in plan:
        print(f"{item.index:>3}. {item.knowledge.id} | {item.knowledge.title} | {item.count} drafts")


async def run_generation(plan: Sequence[GenerationPlanItem], args: argparse.Namespace, target_tags: Sequence[str]) -> int:
    created_total = 0
    failures = 0
    target_dimensions = [args.dimension] if args.dimension else []
    target_secondary_dimensions = [args.secondary_dimension] if args.secondary_dimension else []

    for item in plan:
        print("")
        print(f"[{item.index}/{len(plan)}] generating {item.count} draft(s) for: {item.knowledge.title}")
        request = GenerateDraftRequest(
            knowledgeIds=[item.knowledge.id],
            requirement=args.requirement,
            targetDimensions=target_dimensions,
            targetSecondaryDimensions=target_secondary_dimensions,
            targetTags=list(target_tags),
            count=item.count,
            provider=args.provider,
            model=args.model,
        )

        try:
            drafts = await generate_drafts(request)
        except Exception as exc:
            failures += 1
            print(f"  failed: {exc}", file=sys.stderr)
            if args.stop_on_error:
                break
            continue

        created_total += len(drafts)
        print(f"  created drafts: {len(drafts)}")

        if args.pause_seconds > 0 and item.index < len(plan):
            await asyncio.sleep(args.pause_seconds)

    print("")
    print("Generation finished")
    print(f"- created drafts: {created_total}")
    print(f"- failed knowledge entries: {failures}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate AI literacy question drafts from local knowledge entries."
    )
    parser.add_argument(
        "--per-knowledge",
        type=int,
        default=3,
        help="Draft count to generate for each selected knowledge entry. Maximum 20.",
    )
    parser.add_argument(
        "--max-knowledge",
        type=int,
        default=5,
        help="Maximum knowledge entries to process. Use 0 for no limit.",
    )
    parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="Specific knowledge entry id to process. Can be repeated.",
    )
    parser.add_argument(
        "--dimension",
        default="",
        help="Target primary dimension to pass into the generator.",
    )
    parser.add_argument(
        "--secondary-dimension",
        default="",
        help="Target secondary dimension to pass into the generator.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Target/filter tag. Can be repeated or comma-separated.",
    )
    parser.add_argument(
        "--requirement",
        default="",
        help="Additional generation requirement prompt.",
    )
    parser.add_argument(
        "--provider",
        default="xfyun",
        choices=["xfyun", "deepseek"],
        help="LLM provider.",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Model id. Defaults to the selected provider's model setting from .env.local.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0,
        help="Pause between knowledge entries to reduce API pressure.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the loop after the first failed knowledge entry.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generation plan without calling the API or writing drafts.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    target_tags = _split_csv(args.tag)
    knowledge_ids = _split_csv(args.knowledge_id)

    if args.per_knowledge < 1 or args.per_knowledge > 20:
        parser.error("--per-knowledge must be between 1 and 20")
    if args.max_knowledge < 0:
        parser.error("--max-knowledge must be 0 or greater")
    if args.pause_seconds < 0:
        parser.error("--pause-seconds must be 0 or greater")
    if args.secondary_dimension and not args.dimension:
        parser.error("--secondary-dimension requires --dimension")

    init_db()
    seed_framework()
    entries = _select_knowledge(
        entries=list_knowledge(),
        knowledge_ids=knowledge_ids,
        tags=target_tags,
        max_knowledge=args.max_knowledge,
    )
    plan = _build_plan(entries, args.per_knowledge)
    print_plan(plan, args, target_tags)

    if not plan:
        print("")
        print("No knowledge entries matched the filters.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("")
        print("Dry run only. Remove --dry-run to generate drafts.")
        return 0

    return asyncio.run(run_generation(plan, args, target_tags))


if __name__ == "__main__":
    raise SystemExit(main())
