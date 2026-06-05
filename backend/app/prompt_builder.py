from typing import List

from .framework import format_framework_for_prompt
from .schemas import GenerateDraftRequest, KnowledgeEntry


def _target_text(request: GenerateDraftRequest) -> str:
    parts: List[str] = []
    if request.targetDimensions:
        parts.append("目标一级维度：" + "、".join(request.targetDimensions))
    if request.targetSecondaryDimensions:
        parts.append("目标二级维度：" + "、".join(request.targetSecondaryDimensions))
    if request.targetTags:
        parts.append("目标知识点标签：" + "、".join(request.targetTags))

    if not parts:
        return "未指定结构化目标，请根据知识条目和出题要求自行选择合适的 UACE 维度。"

    return (
        "\n".join(parts)
        + "\n请优先围绕以上目标生成题目；若指定了二级维度，dimension 和 secondaryDimension 必须与所选目标匹配；"
        + "若指定了标签，请将题目场景和 tags 字段聚焦这些知识点。"
    )


def build_generation_requirement(request: GenerateDraftRequest) -> str:
    parts: List[str] = []
    if request.requirement.strip():
        parts.append(request.requirement.strip())
    if request.targetDimensions:
        parts.append("目标一级维度：" + "、".join(request.targetDimensions))
    if request.targetSecondaryDimensions:
        parts.append("目标二级维度：" + "、".join(request.targetSecondaryDimensions))
    if request.targetTags:
        parts.append("目标知识点标签：" + "、".join(request.targetTags))
    return "\n".join(parts)


def build_draft_prompt(
    request: GenerateDraftRequest,
    knowledge_entries: List[KnowledgeEntry],
) -> str:
    knowledge_text = "\n\n".join(
        f"#{index + 1} {entry.title}\n{entry.content}"
        for index, entry in enumerate(knowledge_entries)
    )
    count = max(1, min(request.count, 20))

    return "\n\n".join(
        [
            "你是 AI 素养测评题库出题助手。",
            "请基于给定知识条目生成场景化单选题草稿。",
            f"出题要求：{request.requirement or '无'}",
            "结构化出题目标：\n" + _target_text(request),
            f"题目数量：{count}",
            "每题需要包含题干、场景、4 个选项、正确答案、解析、维度、能力、认知层级、难度、标签和来源。",
            "请为每道题同时给出 dimension（一级维度）、secondaryDimension（二级维度）和 subSkill（二级能力），不要把二级维度和二级能力混为同一字段。",
            "UACE 框架维度如下，dimension 和 secondaryDimension 必须从这里逐字选择，且二级维度必须属于所选一级维度：\n"
            + format_framework_for_prompt(),
            "知识条目：",
            knowledge_text,
        ]
    )


def build_messages(request: GenerateDraftRequest, knowledge_entries: List[KnowledgeEntry]):
    return [
        {
            "role": "system",
            "content": (
                "你是 AI 素养测评题库出题助手。只输出合法 JSON，不要输出 Markdown。"
                'JSON 格式必须是 {"questions":[...]}。'
            ),
        },
        {
            "role": "user",
            "content": build_draft_prompt(request, knowledge_entries)
            + """

请严格输出 JSON object，格式为 {"questions":[...]}。
questions 数组中每个元素字段如下：
title, question, scenario, options, correctAnswer, explanation, dimension, secondaryDimension, subSkill, cognitiveLevel, difficultyEstimate, tags, sourceReference, status。
options 必须是 4 个选项，id 使用 A/B/C/D。
correctAnswer 必须是 A/B/C/D 之一。
cognitiveLevel 只能是 remember/understand/apply/analyze/evaluate/create。
difficultyEstimate 只能是 easy/medium/hard。
status 使用 draft。""",
        },
    ]
