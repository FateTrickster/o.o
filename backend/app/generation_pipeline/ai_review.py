from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from backend.app.config import get_kimi_api_key, get_kimi_base_url, get_kimi_model

from .providers import _extract_json, _post_json
from .types import PipelineCandidate, TaskSpec


def _as_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _build_review_messages(candidate: PipelineCandidate, task: TaskSpec) -> List[Dict[str, str]]:
    question = candidate.question
    point = candidate.knowledge_point
    payload = {
        "task": {
            "requirement": task.requirement,
            "questionType": task.question_type,
            "difficultyTarget": task.difficulty_target,
            "cognitiveLevelTarget": task.cognitive_level_target,
            "minScore": task.ai_review_min_score,
        },
        "knowledgePoint": {
            "knowledgeCode": point.knowledge_code,
            "stage": point.stage,
            "primaryDimension": point.primary_dimension,
            "secondaryDimension": point.secondary_dimension,
            "tertiaryAbility": point.tertiary_ability,
            "knowledgePoint": point.knowledge_point,
            "description": point.description,
            "cognitiveLevel": point.cognitive_level,
        },
        "ruleReview": {
            "structureResult": candidate.review.structure_result,
            "structureIssues": candidate.review.structure_issues,
            "qualityLevel": candidate.review.quality_level,
            "qualityIssues": candidate.review.quality_issues,
            "duplicateScore": candidate.review.duplicate_score,
            "duplicateWith": candidate.review.duplicate_with,
        },
        "question": {
            "provider": question.provider,
            "questionType": question.question_type,
            "title": question.title,
            "scenario": question.scenario,
            "question": question.question,
            "options": question.options,
            "correctAnswer": question.correct_answer,
            "explanation": question.explanation,
            "dimension": question.dimension,
            "secondaryDimension": question.secondary_dimension,
            "tertiaryDimension": question.tertiary_dimension,
            "quaternaryDimension": question.quaternary_dimension,
            "cognitiveLevel": question.cognitive_level,
            "difficultyEstimate": question.difficulty_estimate,
            "tags": question.tags,
            "knowledgePoints": question.knowledge_points,
        },
    }
    system = (
        "你是AI素养测评题库的审题专家。请严格审核题目是否适合进入题库草稿。"
        "重点检查：知识点匹配、维度匹配、认知层级匹配、难度匹配、选项区分度、解析质量、事实准确性、伦理风险。"
        "只输出JSON，不要输出Markdown。"
    )
    user = (
        "请审核下面这道题。评分范围0-100，75分及以上才建议通过。"
        "如果题目只是泛泛谈AI、没有明确考到指定知识点，必须扣分。"
        "如果正确答案有争议、干扰项明显过弱、解析不能解释为什么对/错，也要扣分。\n\n"
        "请按以下JSON格式输出：\n"
        "{\n"
        '  "passed": true,\n'
        '  "score": 86,\n'
        '  "level": "A|B|C|D",\n'
        '  "issues": ["问题1"],\n'
        '  "suggestions": ["修改建议1"],\n'
        '  "dimensionMatch": 0.9,\n'
        '  "difficultyMatch": 0.8,\n'
        '  "knowledgeMatch": 0.95,\n'
        '  "riskFlags": []\n'
        "}\n\n"
        f"待审核数据：{json.dumps(payload, ensure_ascii=False)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _call_kimi_review(candidate: PipelineCandidate, task: TaskSpec) -> Dict[str, Any]:
    base_url = get_kimi_base_url()
    payload = {
        "model": get_kimi_model(),
        "messages": _build_review_messages(candidate, task),
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
    }
    response = _post_json(
        f"{base_url}/chat/completions",
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_kimi_api_key()}",
        },
        payload,
    )
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    return _extract_json(content)


async def ai_review_candidates(candidates: Iterable[PipelineCandidate], task: TaskSpec) -> List[str]:
    if not task.ai_review_enabled:
        return []

    errors: List[str] = []
    provider = (task.ai_review_provider or "kimi").lower()
    if provider != "kimi":
        return [f"AI review provider is not supported yet: {task.ai_review_provider}"]

    for index, candidate in enumerate(candidates, start=1):
        review = candidate.review
        review.ai_review_provider = provider

        if not review.passed:
            review.ai_review_passed = False
            review.ai_review_level = "SKIPPED"
            review.ai_review_issues = ["规则校验未通过，跳过AI审核"]
            continue

        try:
            result = _call_kimi_review(candidate, task)
            score = int(float(result.get("score") or 0))
            model_passed = bool(result.get("passed")) and score >= task.ai_review_min_score
            review.ai_review_score = max(0, min(100, score))
            review.ai_review_level = str(result.get("level") or "").strip()
            review.ai_review_issues = _as_string_list(result.get("issues"))
            review.ai_review_suggestions = _as_string_list(result.get("suggestions"))
            review.ai_review_passed = model_passed
            review.passed = review.passed and model_passed
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            errors.append(f"ai-review {provider} candidate {index}: {message}")
            review.ai_review_passed = False
            review.ai_review_level = "ERROR"
            review.ai_review_issues = [message]
            review.passed = False

    return errors
