from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Sequence

from backend.app.generation_pipeline.prompts import build_structured_prompt
from backend.app.generation_pipeline.runner import run_pipeline
from backend.app.generation_pipeline.selector import select_knowledge_points
from backend.app.generation_pipeline.task_config import load_task_spec, split_csv, task_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the maintainable knowledge-point based question generation pipeline."
    )
    parser.add_argument("--config", help="Optional JSON task config file.")
    parser.add_argument("--name", default="", help="Task name for reports.")
    parser.add_argument("--stage", default="", help="Target stage, for example 初中.")
    parser.add_argument("--dimension", action="append", default=[], help="Primary dimension. Repeat or comma-separate.")
    parser.add_argument(
        "--secondary-dimension",
        action="append",
        default=[],
        help="Secondary dimension. Repeat or comma-separate.",
    )
    parser.add_argument("--knowledge-code", action="append", default=[], help="Knowledge code. Repeat or comma-separate.")
    parser.add_argument(
        "--provider",
        action="append",
        default=[],
        help="Provider: mock, xfyun, deepseek, kimi. Repeat or comma-separate.",
    )
    parser.add_argument("--question-type", default="", help="Question type, default 单选题.")
    parser.add_argument("--count-per-knowledge-point", type=int, default=None)
    parser.add_argument("--limit-per-dimension", type=int, default=None)
    parser.add_argument("--max-knowledge-points", type=int, default=None)
    parser.add_argument("--prompt-batch-size", type=int, default=None)
    parser.add_argument("--difficulty", default="", help="easy, medium, hard, or a local label.")
    parser.add_argument("--cognitive-level", default="", help="remember/understand/apply/analyze/evaluate/create.")
    parser.add_argument("--requirement", default="", help="Additional generation requirement.")
    parser.add_argument("--similarity-threshold", type=float, default=None)
    parser.add_argument("--ai-review", action="store_true", help="Use an AI reviewer after rule-based review.")
    parser.add_argument("--ai-review-provider", default="", help="AI review provider, currently kimi.")
    parser.add_argument("--ai-review-min-score", type=int, default=None, help="Minimum AI review score to pass.")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--write-drafts", action="store_true", help="Write passed candidates into question_drafts.")
    parser.add_argument("--dry-run", action="store_true", help="Print task and selected knowledge points only.")
    parser.add_argument("--show-prompt", action="store_true", help="Print the first structured prompt.")
    return parser


def _overrides(args: argparse.Namespace) -> dict:
    return {
        "name": args.name,
        "stage": args.stage,
        "dimensions": split_csv(args.dimension),
        "secondaryDimensions": split_csv(args.secondary_dimension),
        "knowledgeCodes": split_csv(args.knowledge_code),
        "providers": split_csv(args.provider),
        "questionType": args.question_type,
        "countPerKnowledgePoint": args.count_per_knowledge_point,
        "limitPerDimension": args.limit_per_dimension,
        "maxKnowledgePoints": args.max_knowledge_points,
        "promptBatchSize": args.prompt_batch_size,
        "difficultyTarget": args.difficulty,
        "cognitiveLevelTarget": args.cognitive_level,
        "requirement": args.requirement,
        "similarityThreshold": args.similarity_threshold,
        "aiReviewEnabled": args.ai_review,
        "aiReviewProvider": args.ai_review_provider,
        "aiReviewMinScore": args.ai_review_min_score,
        "outputDir": args.output_dir,
        "writeDrafts": args.write_drafts,
    }


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    for name in ["count_per_knowledge_point", "limit_per_dimension", "max_knowledge_points", "prompt_batch_size"]:
        value = getattr(args, name)
        if value is not None and value < 0:
            parser.error(f"--{name.replace('_', '-')} must be 0 or greater")
    if args.count_per_knowledge_point is not None and args.count_per_knowledge_point < 1:
        parser.error("--count-per-knowledge-point must be 1 or greater")
    if args.prompt_batch_size is not None and args.prompt_batch_size < 1:
        parser.error("--prompt-batch-size must be 1 or greater")
    if args.similarity_threshold is not None and not 0 <= args.similarity_threshold <= 1:
        parser.error("--similarity-threshold must be between 0 and 1")
    if args.ai_review_min_score is not None and not 0 <= args.ai_review_min_score <= 100:
        parser.error("--ai-review-min-score must be between 0 and 100")


def _print_plan(task, points) -> None:
    print("Question generation pipeline plan")
    print(json.dumps(task_to_dict(task), ensure_ascii=False, indent=2))
    print("")
    print(f"Selected knowledge points: {len(points)}")
    planned = len(points) * len(task.providers) * task.count_per_knowledge_point
    print(f"Planned generated candidates: {planned}")
    print("")
    for index, point in enumerate(points, start=1):
        print(
            f"{index:>3}. {point.knowledge_code} | {point.stage} | "
            f"{point.primary_dimension} > {point.secondary_dimension} > "
            f"{point.tertiary_ability} > {point.knowledge_point}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)

    task = load_task_spec(args.config, _overrides(args))
    points = select_knowledge_points(task)
    _print_plan(task, points)

    if args.show_prompt and points:
        print("")
        print("First structured prompt")
        print(json.dumps(build_structured_prompt(task, points[: task.prompt_batch_size]), ensure_ascii=False, indent=2))

    if args.dry_run:
        print("")
        print("Dry run only. Remove --dry-run to generate candidates.")
        return 0 if points else 1

    if not points:
        print("No knowledge points matched the task configuration.", file=sys.stderr)
        return 1

    report = asyncio.run(run_pipeline(task))
    print("")
    print("Pipeline finished")
    print(f"- generated candidates: {len(report.candidates)}")
    print(f"- created drafts: {report.created_drafts}")
    print(f"- errors: {len(report.errors)}")
    print(f"- report json: {Path(report.report_json)}")
    print(f"- report csv: {Path(report.report_csv)}")
    if report.errors:
        for error in report.errors:
            print(f"  - {error}", file=sys.stderr)
    return 1 if report.errors and not report.candidates else 0


if __name__ == "__main__":
    raise SystemExit(main())
