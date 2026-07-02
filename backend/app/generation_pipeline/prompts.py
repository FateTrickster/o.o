from __future__ import annotations

from typing import Dict, List

from .types import KnowledgePointContext, TaskSpec


def _point_block(index: int, point: KnowledgePointContext) -> str:
    return "\n".join(
        [
            f"{index}. knowledgeCode: {point.knowledge_code}",
            f"学段: {point.stage}",
            f"一级维度: {point.primary_dimension}",
            f"二级维度: {point.secondary_dimension}",
            f"三级能力: {point.tertiary_ability}",
            f"四级知识点: {point.knowledge_point}",
            f"知识点说明: {point.description}",
            f"来源: {'；'.join(point.source_references)}",
        ]
    )


def build_structured_prompt(task: TaskSpec, points: List[KnowledgePointContext]) -> List[Dict[str, str]]:
    count = task.count_per_knowledge_point
    point_text = "\n\n".join(_point_block(index, point) for index, point in enumerate(points, start=1))
    extra_requirement = task.requirement.strip() or "无额外要求"

    user_prompt = f"""
请基于给定 AI 素养知识点生成题目草稿。

任务配置：
- 题型：{task.question_type}
- 每个知识点生成数量：{count}
- 目标难度：{task.difficulty_target}
- 目标认知层级：{task.cognitive_level_target or "由知识点和题型决定"}
- 目标标签/知识点：{"、".join(task.target_tags) if task.target_tags else "未限定"}
- 额外要求：{extra_requirement}

硬性规则：
1. 必须严格围绕给定 knowledgeCode 出题，不要新增 knowledgeCode。
2. 每个 knowledgeCode 生成 {count} 道题。
3. 如果题型是单选，options 必须是 A/B/C/D 四个选项，correctAnswer 只能是 A/B/C/D。
4. 题目应贴近中学生学习、校园生活或日常 AI 使用情境。
5. 不要直接照抄知识点说明，要把知识点转化为判断、应用、辨析或方案选择任务。
6. dimension、secondaryDimension、tertiaryDimension、quaternaryDimension 必须沿用给定知识点。
7. 只输出合法 JSON object，不要 Markdown，不要解释。

输出 JSON 格式：
{{
  "questions": [
    {{
      "knowledgeCode": "...",
      "questionType": "{task.question_type}",
      "title": "短标题",
      "scenario": "场景材料",
      "question": "题干或作答问题",
      "options": [{{"id":"A","text":"..."}}, {{"id":"B","text":"..."}}, {{"id":"C","text":"..."}}, {{"id":"D","text":"..."}}],
      "correctAnswer": "A",
      "explanation": "解析或参考答案说明",
      "dimension": "一级维度",
      "secondaryDimension": "二级维度",
      "tertiaryDimension": "三级能力",
      "quaternaryDimension": "四级知识点",
      "knowledgePoints": ["四级知识点"],
      "cognitiveLevel": "remember/understand/apply/analyze/evaluate/create",
      "difficultyEstimate": "easy/medium/hard",
      "tags": ["标签"]
    }}
  ]
}}

知识点：
{point_text}
""".strip()

    return [
        {
            "role": "system",
            "content": "你是 AI 素养测评题库出题专家。你只输出合法 JSON object。",
        },
        {"role": "user", "content": user_prompt},
    ]
