from __future__ import annotations

import asyncio
import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List

from backend.app.config import (
    get_deepseek_api_key,
    get_deepseek_base_url,
    get_deepseek_model,
    get_kimi_api_key,
    get_kimi_base_url,
    get_kimi_model,
    get_xfyun_api_key,
    get_xfyun_base_url,
    get_xfyun_model,
)

from .prompts import build_structured_prompt
from .types import GeneratedQuestion, KnowledgePointContext, TaskSpec


def _strip_code_fence(content: str) -> str:
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_json(content: str) -> Dict[str, Any]:
    cleaned = _strip_code_fence(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        message = payload.get("error", {}).get("message") if isinstance(payload, dict) else ""
        raise RuntimeError(message or f"HTTP {exc.code}: {body[:300]}") from exc


def _normalize_options(raw_options: Any) -> List[Dict[str, str]]:
    if isinstance(raw_options, dict):
        return [
            {"id": str(key).strip(), "text": str(value).strip()}
            for key, value in raw_options.items()
            if str(key).strip() and str(value).strip()
        ]
    if isinstance(raw_options, list):
        result: List[Dict[str, str]] = []
        for index, item in enumerate(raw_options):
            default_id = chr(65 + index)
            if isinstance(item, dict):
                option_id = str(item.get("id") or item.get("key") or item.get("label") or default_id).strip()
                text = str(item.get("text") or item.get("content") or item.get("value") or "").strip()
            else:
                option_id = default_id
                text = str(item).strip()
            if option_id and text:
                result.append({"id": option_id, "text": text})
        return result
    return []


def _normalize_answer(value: Any) -> str:
    if isinstance(value, list):
        return "".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _normalize_tags(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,，；;\n]", value) if item.strip()]
    return []


def _find_point(raw: Dict[str, Any], points: List[KnowledgePointContext]) -> KnowledgePointContext:
    knowledge_code = str(raw.get("knowledgeCode") or raw.get("knowledge_code") or "").strip()
    for point in points:
        if point.knowledge_code == knowledge_code:
            return point
    for point in points:
        if point.knowledge_point and point.knowledge_point in str(raw):
            return point
    return points[0]


def normalize_question(provider: str, raw: Dict[str, Any], points: List[KnowledgePointContext], task: TaskSpec) -> GeneratedQuestion:
    point = _find_point(raw, points)
    tags = _normalize_tags(raw.get("tags"))
    for tag in [point.stage, point.primary_dimension, point.tertiary_ability, point.knowledge_point, f"provider:{provider}"]:
        if tag and tag not in tags:
            tags.append(tag)
    return GeneratedQuestion(
        provider=provider,
        knowledge_code=point.knowledge_code,
        question_type=str(raw.get("questionType") or task.question_type).strip(),
        title=str(raw.get("title") or point.knowledge_point).strip(),
        scenario=str(raw.get("scenario") or "").strip(),
        question=str(raw.get("question") or "").strip(),
        options=_normalize_options(raw.get("options")),
        correct_answer=_normalize_answer(raw.get("correctAnswer")),
        explanation=str(raw.get("explanation") or "").strip(),
        dimension=str(raw.get("dimension") or point.primary_dimension).strip(),
        secondary_dimension=str(raw.get("secondaryDimension") or point.secondary_dimension).strip(),
        tertiary_dimension=str(raw.get("tertiaryDimension") or point.tertiary_ability).strip(),
        quaternary_dimension=str(raw.get("quaternaryDimension") or point.knowledge_point).strip(),
        cognitive_level=str(raw.get("cognitiveLevel") or task.cognitive_level_target or point.cognitive_level or "apply").strip(),
        difficulty_estimate=str(raw.get("difficultyEstimate") or task.difficulty_target or "medium").strip(),
        tags=tags,
        knowledge_points=_normalize_tags(raw.get("knowledgePoints")) or [point.knowledge_point],
        source_reference="；".join(point.source_references),
        raw=raw,
    )


def mock_generate(points: List[KnowledgePointContext], task: TaskSpec, provider: str = "mock") -> List[GeneratedQuestion]:
    questions: List[GeneratedQuestion] = []
    for point in points:
        for index in range(task.count_per_knowledge_point):
            raw = {
                "knowledgeCode": point.knowledge_code,
                "questionType": task.question_type,
                "title": f"{point.knowledge_point}情境判断",
                "scenario": f"信息科技课上，同学们正在讨论“{point.knowledge_point}”在学习生活中的应用。",
                "question": f"下列哪一项最能体现对“{point.knowledge_point}”的正确理解？",
                "options": [
                    {"id": "A", "text": "只看 AI 工具是否方便，不需要理解其使用边界。"},
                    {"id": "B", "text": f"结合具体任务和“{point.description or point.knowledge_point}”进行判断。"},
                    {"id": "C", "text": "只要 AI 给出答案，就可以直接作为最终结论。"},
                    {"id": "D", "text": "所有自动化软件都可以视为完全相同的 AI 系统。"},
                ],
                "correctAnswer": "B",
                "explanation": f"本题考查 {point.knowledge_point}。关键是结合知识点说明和具体情境判断，而不是只记忆工具名称。",
                "dimension": point.primary_dimension,
                "secondaryDimension": point.secondary_dimension,
                "tertiaryDimension": point.tertiary_ability,
                "quaternaryDimension": point.knowledge_point,
                "cognitiveLevel": task.cognitive_level_target or point.cognitive_level or "apply",
                "difficultyEstimate": task.difficulty_target,
                "tags": ["mock", point.knowledge_point],
                "knowledgePoints": [point.knowledge_point],
            }
            if task.count_per_knowledge_point > 1:
                raw["title"] = f"{raw['title']}-{index + 1}"
            questions.append(normalize_question(provider, raw, [point], task))
    return questions


async def api_generate(
    provider: str,
    points: List[KnowledgePointContext],
    task: TaskSpec,
    rag_context_by_knowledge_code: Dict[str, List[Dict[str, Any]]] | None = None,
) -> List[GeneratedQuestion]:
    messages = build_structured_prompt(task, points, rag_context_by_knowledge_code)
    if provider == "xfyun":
        api_key = get_xfyun_api_key()
        base_url = get_xfyun_base_url()
        model = get_xfyun_model()
        payload = {"model": model, "messages": messages, "temperature": 0.35}
    elif provider == "deepseek":
        api_key = get_deepseek_api_key()
        base_url = get_deepseek_base_url()
        model = get_deepseek_model()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.35,
            "response_format": {"type": "json_object"},
        }
    elif provider == "kimi":
        api_key = get_kimi_api_key()
        base_url = get_kimi_base_url()
        model = get_kimi_model()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
        }
    else:
        raise ValueError(f"Unsupported API provider: {provider}")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        _post_json,
        f"{base_url}/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload,
    )
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = _extract_json(content)
    raw_questions = parsed.get("questions")
    if not isinstance(raw_questions, list):
        raise RuntimeError(f"{provider} response missing questions array")
    return [normalize_question(provider, raw, points, task) for raw in raw_questions]


async def generate_for_provider(
    provider: str,
    points: List[KnowledgePointContext],
    task: TaskSpec,
    rag_context_by_knowledge_code: Dict[str, List[Dict[str, Any]]] | None = None,
) -> List[GeneratedQuestion]:
    if provider == "mock":
        return mock_generate(points, task)
    return await api_generate(provider, points, task, rag_context_by_knowledge_code)
