from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List, Tuple

from backend.app.repositories import list_drafts, list_questions

from .types import GeneratedQuestion, KnowledgePointContext, PipelineCandidate, ReviewResult, TaskSpec


def infer_tags(question: GeneratedQuestion, point: KnowledgePointContext) -> List[str]:
    text = " ".join([question.title, question.scenario, question.question, question.explanation, point.description])
    tags = list(dict.fromkeys([*question.tags, point.stage, point.primary_dimension, point.knowledge_point]))
    keyword_tags = {
        "数据": ["数据", "训练集", "隐私", "样本"],
        "算法": ["算法", "模型", "分类", "预测", "聚类"],
        "生成式AI": ["生成", "提示词", "文案", "图像", "文本"],
        "AI伦理": ["隐私", "公平", "偏见", "责任", "诚信", "版权"],
        "校园场景": ["学校", "班级", "老师", "同学", "课堂", "作业", "校园"],
    }
    for tag, keywords in keyword_tags.items():
        if any(keyword in text for keyword in keywords) and tag not in tags:
            tags.append(tag)
    return [tag for tag in tags if tag]


def infer_cognitive_level(question: GeneratedQuestion, point: KnowledgePointContext, task: TaskSpec) -> str:
    if task.cognitive_level_target:
        return task.cognitive_level_target
    text = question.question + question.scenario
    if any(token in text for token in ["设计", "提出方案", "改进", "规划"]):
        return "create"
    if any(token in text for token in ["评价", "判断", "比较", "分析", "识别风险"]):
        return "analyze"
    if any(token in text for token in ["选择", "应用", "使用", "处理"]):
        return "apply"
    if point.primary_dimension == "创造AI（Create）":
        return "create"
    if point.primary_dimension == "AI伦理（Ethics）":
        return "evaluate"
    if point.primary_dimension == "理解AI（Understand）":
        return "understand"
    return "apply"


def calibrate_difficulty(question: GeneratedQuestion, task: TaskSpec) -> str:
    if task.difficulty_target in {"easy", "medium", "hard"}:
        base = task.difficulty_target
    else:
        base = question.difficulty_estimate if question.difficulty_estimate in {"easy", "medium", "hard"} else "medium"
    length = len(question.scenario) + len(question.question) + sum(len(option.get("text", "")) for option in question.options)
    if length > 420:
        return "hard"
    if length < 160 and base == "medium":
        return "easy"
    return base


def structure_review(question: GeneratedQuestion) -> Tuple[str, List[str]]:
    issues: List[str] = []
    option_ids = {option.get("id", "").strip() for option in question.options}
    if not question.knowledge_code:
        issues.append("缺少 knowledgeCode")
    if not question.title:
        issues.append("标题为空")
    if not question.question:
        issues.append("题干为空")
    if not question.scenario or len(question.scenario) < 8:
        issues.append("场景为空或过短")
    if question.question_type == "单选":
        if len(question.options) != 4:
            issues.append(f"单选题选项数为 {len(question.options)}")
        if question.correct_answer not in option_ids:
            issues.append("正确答案未匹配选项编号")
    if not question.explanation or len(question.explanation) < 15:
        issues.append("解析为空或过短")
    if not question.dimension or not question.secondary_dimension:
        issues.append("维度字段不完整")
    return ("通过" if not issues else "不通过" if any("题干为空" in issue or "正确答案" in issue for issue in issues) else "需修正", issues)


def quality_review(question: GeneratedQuestion, point: KnowledgePointContext, structure_result: str) -> Tuple[str, List[str]]:
    if structure_result == "不通过":
        return "C", ["结构未通过"]
    issues: List[str] = []
    combined = " ".join([question.title, question.scenario, question.question, question.explanation])
    if point.knowledge_point not in combined and point.tertiary_ability not in combined:
        issues.append("考点显性不足")
    if not any(token in question.scenario for token in ["学生", "同学", "老师", "学校", "课堂", "作业", "班级", "校园", "小组"]):
        issues.append("学习或校园场景不明显")
    option_lengths = [len(option.get("text", "")) for option in question.options if option.get("text")]
    if option_lengths and max(option_lengths) > max(20, min(option_lengths) * 3):
        issues.append("选项长度差异过大")
    option_texts = [option.get("text", "").strip() for option in question.options]
    if len(option_texts) != len(set(option_texts)):
        issues.append("选项重复")
    if question.correct_answer and question.question_type == "单选":
        correct = next((option.get("text", "") for option in question.options if option.get("id") == question.correct_answer), "")
        if correct and any(token in correct for token in ["一定", "所有", "完全", "只要"]) and "不" not in correct:
            issues.append("正确选项表述可能过绝对")
    if not any(token in question.explanation for token in ["因为", "因此", "关键", "体现", "说明", "不符合", "错误"]):
        issues.append("解析理由不足")
    if not issues:
        return "A", []
    if len(issues) <= 2:
        return "B", issues
    return "C", issues


def _tokens(text: str) -> Counter:
    chars = [char for char in re.sub(r"\s+", "", text.lower()) if char]
    grams = ["".join(chars[index : index + 2]) for index in range(max(0, len(chars) - 1))]
    return Counter(grams or chars)


def cosine_similarity(left: str, right: str) -> float:
    a = _tokens(left)
    b = _tokens(right)
    if not a or not b:
        return 0.0
    dot = sum(a[key] * b.get(key, 0) for key in a)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def question_text(question: GeneratedQuestion) -> str:
    return " ".join([question.scenario, question.question, " ".join(option.get("text", "") for option in question.options)])


def existing_question_texts() -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    for question in list_questions():
        rows.append((f"question:{question.itemCode}", " ".join([question.scenario, question.question])))
    for draft in list_drafts():
        rows.append((f"draft:{draft.id}", " ".join([draft.scenario, draft.question])))
    return rows


def review_candidates(
    generated: Iterable[GeneratedQuestion],
    point_by_code: dict[str, KnowledgePointContext],
    task: TaskSpec,
) -> List[PipelineCandidate]:
    existing = existing_question_texts()
    candidates: List[PipelineCandidate] = []
    batch_texts: List[Tuple[str, str]] = []
    for index, question in enumerate(generated, start=1):
        point = point_by_code[question.knowledge_code]
        question.tags = infer_tags(question, point)
        question.cognitive_level = infer_cognitive_level(question, point, task)
        question.difficulty_estimate = calibrate_difficulty(question, task)
        structure_result, structure_issues = structure_review(question)
        quality_level, quality_issues = quality_review(question, point, structure_result)

        text = question_text(question)
        duplicate_with = ""
        duplicate_score = 0.0
        for label, other_text in [*existing, *batch_texts]:
            score = cosine_similarity(text, other_text)
            if score > duplicate_score:
                duplicate_score = score
                duplicate_with = label
        duplicate_group = "duplicate" if duplicate_score >= task.similarity_threshold else ""
        batch_texts.append((f"batch:{index}", text))
        passed = structure_result == "通过" and duplicate_group != "duplicate"

        review = ReviewResult(
            structure_result=structure_result,
            structure_issues=structure_issues,
            quality_level=quality_level,
            quality_issues=quality_issues,
            tags=question.tags,
            cognitive_level=question.cognitive_level,
            difficulty_estimate=question.difficulty_estimate,
            duplicate_group=duplicate_group,
            duplicate_score=round(duplicate_score, 4),
            duplicate_with=duplicate_with,
            passed=passed,
        )
        candidates.append(PipelineCandidate(question=question, knowledge_point=point, review=review))
    return candidates
