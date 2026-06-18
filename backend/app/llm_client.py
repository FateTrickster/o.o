from typing import Any, Dict, List
import json
import re

import httpx

from .config import (
    get_deepseek_api_key,
    get_deepseek_base_url,
    get_deepseek_model,
    get_xfyun_api_key,
    get_xfyun_base_url,
    get_xfyun_model,
)
from .framework import normalize_framework_selection
from .prompt_builder import build_messages
from .schemas import GenerateDraftRequest, KnowledgeEntry, QuestionInput, QuestionOption


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
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                preview = cleaned[:500].replace("\n", "\\n")
                raise ValueError(f"Model response was not valid JSON: {exc}. Preview: {preview}") from exc
        preview = cleaned[:500].replace("\n", "\\n")
        raise ValueError(f"Model response did not contain a JSON object. Preview: {preview}")


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


def _normalize_question(raw: Dict[str, Any]) -> QuestionInput:
    tags = _normalize_string_list(raw.get("tags"))
    knowledge_points = _normalize_string_list(raw.get("knowledgePoints"))
    selection = normalize_framework_selection(
        raw.get("dimension", ""),
        raw.get("secondaryDimension", ""),
        " ".join(
            [
                raw.get("title", ""),
                raw.get("question", ""),
                raw.get("scenario", ""),
                raw.get("subSkill", ""),
                " ".join(str(tag) for tag in tags),
                " ".join(str(point) for point in knowledge_points),
            ]
        ),
    )
    raw = {**raw, **selection}
    return QuestionInput(
        questionType=str(raw.get("questionType", "单选")).strip() or "单选",
        title=str(raw.get("title", "")).strip(),
        question=str(raw.get("question", "")).strip(),
        scenario=str(raw.get("scenario", "")).strip(),
        options=_normalize_options(raw.get("options")),
        correctAnswer=_normalize_answer(raw.get("correctAnswer")),
        explanation=str(raw.get("explanation", "")).strip(),
        dimension=raw["dimension"],
        secondaryDimension=raw["secondaryDimension"],
        tertiaryDimension=str(raw.get("tertiaryDimension", "")).strip(),
        quaternaryDimension=str(raw.get("quaternaryDimension", "")).strip(),
        subSkill=str(raw.get("subSkill", "")).strip() or raw["secondaryDimension"],
        cognitiveLevel=str(raw.get("cognitiveLevel", "apply")).strip(),
        difficultyEstimate=str(raw.get("difficultyEstimate", "medium")).strip(),
        tags=tags,
        knowledgePoints=knowledge_points,
        sourceReference=str(raw.get("sourceReference", "")).strip(),
        status=str(raw.get("status", "draft")).strip() or "draft",
    )


async def generate_with_xfyun(
    request: GenerateDraftRequest,
    knowledge_entries: List[KnowledgeEntry],
) -> List[QuestionInput]:
    api_key = get_xfyun_api_key()
    base_url = get_xfyun_base_url()
    model = request.model or get_xfyun_model()
    timeout_seconds = max(90, min(240, 45 + request.count * 15))
    payload = {
        "model": model,
        "messages": build_messages(request, knowledge_entries),
        "temperature": 0.4,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, trust_env=False) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"Xfyun MaaS request timed out after {timeout_seconds} seconds. "
            "Try generating fewer questions per batch or narrowing the selected dimensions."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Xfyun MaaS network request failed: {exc}") from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("Xfyun MaaS response was not valid JSON") from exc
    if response.status_code >= 400:
        message = result.get("error", {}).get("message") if isinstance(result, dict) else ""
        raise RuntimeError(message or f"Xfyun MaaS request failed with {response.status_code}")

    content = result.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("Xfyun MaaS response did not include content")

    parsed = _extract_json(content)
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Xfyun MaaS response must include a questions array")

    return [_normalize_question(question) for question in questions]


async def generate_with_deepseek(
    request: GenerateDraftRequest,
    knowledge_entries: List[KnowledgeEntry],
) -> List[QuestionInput]:
    api_key = get_deepseek_api_key()
    base_url = get_deepseek_base_url()
    model = request.model or get_deepseek_model()
    timeout_seconds = max(90, min(240, 45 + request.count * 15))
    payload = {
        "model": model,
        "messages": build_messages(request, knowledge_entries),
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, trust_env=False) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"DeepSeek request timed out after {timeout_seconds} seconds. "
            "Try generating fewer questions per batch or narrowing the selected dimensions."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"DeepSeek network request failed: {exc}") from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("DeepSeek response was not valid JSON") from exc
    if response.status_code >= 400:
        message = result.get("error", {}).get("message") if isinstance(result, dict) else ""
        raise RuntimeError(message or f"DeepSeek request failed with {response.status_code}")

    content = result.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("DeepSeek response did not include content")

    parsed = _extract_json(content)
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("DeepSeek response must include a questions array")

    return [_normalize_question(question) for question in questions]
