import { DraftGenerationContext } from "@/lib/llm/types";
import { formatFrameworkForPrompt } from "@/lib/aiLiteracyFramework";

function buildTargetText(context: DraftGenerationContext) {
  const parts: string[] = [];

  if (context.targetDimensions?.length) {
    parts.push(`目标一级维度：${context.targetDimensions.join("、")}`);
  }

  if (context.targetSecondaryDimensions?.length) {
    parts.push(`目标二级维度：${context.targetSecondaryDimensions.join("、")}`);
  }

  if (context.targetTags?.length) {
    parts.push(`目标知识点标签：${context.targetTags.join("、")}`);
  }

  return parts.length > 0
    ? `${parts.join("\n")}\n请优先围绕以上目标生成题目；若指定了二级维度，dimension 和 secondaryDimension 必须与所选目标匹配；若指定了标签，请将题目场景和 tags 字段聚焦这些知识点。`
    : "未指定结构化目标，请根据知识条目和出题要求自行选择合适的 UACE 维度。";
}

export function buildDraftPrompt(context: DraftGenerationContext) {
  const knowledgeText = context.knowledgeEntries
    .map((entry, index) => `#${index + 1} ${entry.title}\n${entry.content}`)
    .join("\n\n");

  return [
    "你是 AI 素养测评题库出题助手。",
    "请基于给定知识条目生成场景化单选题草稿。",
    `出题要求：${context.requirement || "无"}`,
    `结构化出题目标：\n${buildTargetText(context)}`,
    `题目数量：${context.count ?? 3}`,
    "每题需要包含题干、场景、4 个选项、正确答案、解析、维度、能力、认知层级、难度、标签和来源。",
    "请为每道题同时给出 dimension（一级维度）、secondaryDimension（二级维度）和 subSkill（二级能力），不要把二级维度和二级能力混为同一字段。",
    `UACE 框架维度如下，dimension 和 secondaryDimension 必须从这里逐字选择，且二级维度必须属于所选一级维度：\n${formatFrameworkForPrompt()}`,
    "知识条目：",
    knowledgeText
  ].join("\n\n");
}
