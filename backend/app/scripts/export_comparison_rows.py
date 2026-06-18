from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Tuple

from backend.app.repositories import list_drafts


PROVIDER_NAME = {"xfyun": "讯飞", "deepseek": "DeepSeek", "codex": "Codex"}
DIM_ORDER = ["理解AI（Understand）", "应用AI（Apply）", "创造AI（Create）", "AI伦理（Ethics）"]
DIM_CODE = {
    "理解AI（Understand）": "U",
    "应用AI（Apply）": "A",
    "创造AI（Create）": "C",
    "AI伦理（Ethics）": "E",
}
JOB_MAP: Dict[str, Tuple[str, str]] = {
    "be4b2e05-85ee-4d29-88f6-b16cc8bfcf66": ("xfyun", "理解AI（Understand）"),
    "baf7e751-824f-4ed8-a84f-c59c0c0bb411": ("xfyun", "应用AI（Apply）"),
    "1850a3bb-006b-49bc-a510-661c083d4df5": ("xfyun", "创造AI（Create）"),
    "ec872da0-cfae-4124-9896-e797d35c4bb6": ("xfyun", "AI伦理（Ethics）"),
    "eac61035-8d67-4ea8-b3ec-ab9629dd5a26": ("deepseek", "理解AI（Understand）"),
    "c49eb2af-03dd-4aef-ad32-07c3c7047b7f": ("deepseek", "应用AI（Apply）"),
    "9defaf2b-912f-4028-8960-d10ab1b1752c": ("deepseek", "创造AI（Create）"),
    "df7a648b-7acc-4d36-b066-bd6eb9e62fa3": ("deepseek", "AI伦理（Ethics）"),
    "4739f6b1-77fb-45b0-a946-07dfa827a7af": ("codex", ""),
}


def assess(draft, intended_dimension: str) -> Tuple[str, str, str]:
    issues = []
    if len(draft.options) != 4:
        issues.append(f"选项数为{len(draft.options)}，不是4个")

    option_ids = {option.id for option in draft.options}
    answer_letters = set(re.findall(r"[A-Z]", draft.correctAnswer or ""))
    if not answer_letters or not answer_letters.issubset(option_ids):
        issues.append("正确答案未匹配选项编号")

    if not draft.knowledgePoints:
        issues.append("参考知识点为空")
    if len((draft.explanation or "").strip()) < 30:
        issues.append("解析偏短")
    if intended_dimension and draft.dimension != intended_dimension:
        issues.append(f"维度偏移：计划为{intended_dimension}，题目为{draft.dimension}")
    if len((draft.scenario or "").strip()) < 12:
        issues.append("场景描述偏短")

    scene_text = (draft.scenario or "") + (draft.question or "")
    scene_markers = ["学校", "班级", "同学", "小组", "老师", "校园", "学生", "课堂", "作业", "社团"]
    if not any(marker in scene_text for marker in scene_markers):
        issues.append("校园/学习场景不明显")

    if not issues:
        return "较好：字段完整，场景和考点基本清晰。", "建议入库", "可进入人工复审。"
    if len(issues) <= 2 and not any("正确答案" in issue or "选项数" in issue for issue in issues):
        return "一般：主体可用，但需人工复核。", "修改后入库", "；".join(issues)
    return "较弱：存在结构或定位问题。", "暂不入库", "；".join(issues)


def build_rows():
    rows = []
    for draft in list_drafts():
        mapped = JOB_MAP.get(draft.generationJobId)
        if not mapped:
            continue
        provider, intended_dimension = mapped
        if provider == "codex":
            intended_dimension = draft.dimension

        quality, recommend, note = assess(draft, intended_dimension)
        rows.append(
            {
                "provider": provider,
                "source": PROVIDER_NAME[provider],
                "intendedDimension": intended_dimension,
                "dimension": draft.dimension,
                "knowledgeEntry": "AI素养框架.docx #1",
                "title": draft.title,
                "question": draft.question,
                "scenario": draft.scenario,
                "options": "\n".join(f"{option.id}. {option.text}" for option in draft.options),
                "correctAnswer": draft.correctAnswer,
                "explanation": draft.explanation,
                "knowledgePoints": "；".join(draft.knowledgePoints),
                "quality": quality,
                "recommend": recommend,
                "note": note,
                "createdAt": draft.createdAt,
                "jobId": draft.generationJobId,
            }
        )

    provider_order = {"xfyun": 0, "deepseek": 1, "codex": 2}
    rows.sort(
        key=lambda row: (
            provider_order.get(row["provider"], 9),
            DIM_ORDER.index(row["intendedDimension"]) if row["intendedDimension"] in DIM_ORDER else 99,
            row["createdAt"],
            row["title"],
        )
    )

    counts = defaultdict(int)
    for row in rows:
        counts[(row["provider"], row["intendedDimension"])] += 1
        row["number"] = (
            f"{row['provider'].upper()}-{DIM_CODE.get(row['intendedDimension'], 'X')}-"
            f"{counts[(row['provider'], row['intendedDimension'])]:02d}"
        )
    return rows


def main() -> int:
    rows = build_rows()
    output = Path("data/model_comparison_rows_2026-06-12.json")
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = Counter((row["provider"], row["intendedDimension"]) for row in rows)
    print(f"rows={len(rows)}")
    print("provider_counts=", Counter(row["provider"] for row in rows))
    print("recommend_counts=", Counter(row["recommend"] for row in rows))
    for key, value in sorted(counts.items()):
        print(key, value)
    return 0 if len(rows) == 60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
