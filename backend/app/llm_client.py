from typing import Any, Dict, List
import json
import re

import httpx

from .config import get_xfyun_api_key, get_xfyun_base_url, get_xfyun_model
from .framework import normalize_framework_selection
from .prompt_builder import build_messages
from .schemas import GenerateDraftRequest, KnowledgeEntry, QuestionInput


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


def _normalize_question(raw: Dict[str, Any]) -> QuestionInput:
    tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
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
            ]
        ),
    )
    raw = {**raw, **selection}
    return QuestionInput(
        title=str(raw.get("title", "")).strip(),
        question=str(raw.get("question", "")).strip(),
        scenario=str(raw.get("scenario", "")).strip(),
        options=raw.get("options") or [],
        correctAnswer=str(raw.get("correctAnswer", "")).strip(),
        explanation=str(raw.get("explanation", "")).strip(),
        dimension=raw["dimension"],
        secondaryDimension=raw["secondaryDimension"],
        subSkill=str(raw.get("subSkill", "")).strip() or raw["secondaryDimension"],
        cognitiveLevel=str(raw.get("cognitiveLevel", "apply")).strip(),
        difficultyEstimate=str(raw.get("difficultyEstimate", "medium")).strip(),
        tags=[str(tag).strip() for tag in tags if str(tag).strip()],
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
    payload = {
        "model": model,
        "messages": build_messages(request, knowledge_entries),
        "temperature": 0.4,
    }

    async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    result = response.json()
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
