import { buildDraftPrompt } from "@/lib/llm/prompts";
import { DraftGenerationContext, DraftQuestionProvider } from "@/lib/llm/types";
import { QuestionInput } from "@/types/question";

type KimiMessage = {
  role: "system" | "user";
  content: string;
};

type KimiResponse = {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
  error?: {
    message?: string;
  };
};

function stripCodeFence(content: string) {
  return content
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();
}

function parseQuestions(content: string) {
  const parsed = JSON.parse(stripCodeFence(content)) as QuestionInput[] | { questions?: QuestionInput[] };
  if (Array.isArray(parsed)) {
    return parsed;
  }
  if (Array.isArray(parsed.questions)) {
    return parsed.questions;
  }
  throw new Error("Kimi response must include a questions array");
}

function buildMessages(context: DraftGenerationContext): KimiMessage[] {
  return [
    {
      role: "system",
      content: "你是 AI 素养测评题库出题助手。只输出合法 JSON object，不要输出 Markdown。"
    },
    {
      role: "user",
      content: `${buildDraftPrompt(context)}

请严格输出 JSON object，格式为 {"questions":[...]}。questions 数组中每个元素字段如下：
title, question, scenario, options, correctAnswer, explanation, dimension, secondaryDimension, subSkill, cognitiveLevel, difficultyEstimate, tags, sourceReference, status。
options 必须是 4 个选项，id 使用 A/B/C/D。correctAnswer 必须是 A/B/C/D 之一。
cognitiveLevel 只能是 remember/understand/apply/analyze/evaluate/create。
difficultyEstimate 只能是 easy/medium/hard。status 使用 draft。`
    }
  ];
}

export const kimiProvider: DraftQuestionProvider = {
  async generateDraftQuestions(context: DraftGenerationContext) {
    const apiKey = process.env.AI_LITERACY_KIMI_API_KEY || process.env.KIMI_API_KEY || process.env.MOONSHOT_API_KEY;
    if (!apiKey) {
      throw new Error("AI_LITERACY_KIMI_API_KEY, KIMI_API_KEY, or MOONSHOT_API_KEY is not configured");
    }

    const baseUrl = process.env.KIMI_BASE_URL ?? "https://api.moonshot.cn/v1";
    const model = process.env.KIMI_MODEL ?? "kimi-k2.6";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model,
        messages: buildMessages(context),
        temperature: 0.6,
        response_format: { type: "json_object" },
        thinking: { type: "disabled" }
      })
    });

    const result = (await response.json()) as KimiResponse;
    if (!response.ok) {
      throw new Error(result.error?.message || `Kimi request failed with ${response.status}`);
    }

    const content = result.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error("Kimi response did not include content");
    }

    return parseQuestions(content);
  }
};
