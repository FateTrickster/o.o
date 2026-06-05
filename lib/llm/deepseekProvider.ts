import { buildDraftPrompt } from "@/lib/llm/prompts";
import { DraftGenerationContext, DraftQuestionProvider } from "@/lib/llm/types";
import { QuestionInput } from "@/types/question";

type DeepSeekMessage = {
  role: "system" | "user";
  content: string;
};

type DeepSeekResponse = {
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
  const parsed = JSON.parse(stripCodeFence(content)) as QuestionInput[];
  if (!Array.isArray(parsed)) {
    throw new Error("DeepSeek response must be a JSON array");
  }

  return parsed;
}

function buildMessages(context: DraftGenerationContext): DeepSeekMessage[] {
  return [
    {
      role: "system",
      content:
        "你是 AI 素养测评题库出题助手。只输出 JSON object，不要输出 Markdown。"
    },
    {
      role: "user",
      content: `${buildDraftPrompt(context)}

请严格输出 JSON object，格式为 {"questions":[...]}。
questions 数组中每个元素字段如下：
title, question, scenario, options, correctAnswer, explanation, dimension, secondaryDimension, subSkill, cognitiveLevel, difficultyEstimate, tags, sourceReference, status。
options 必须是 4 个选项，id 使用 A/B/C/D。
correctAnswer 必须是 A/B/C/D 之一。
cognitiveLevel 只能是 remember/understand/apply/analyze/evaluate/create。
difficultyEstimate 只能是 easy/medium/hard。
status 使用 draft。`
    }
  ];
}

export const deepseekProvider: DraftQuestionProvider = {
  async generateDraftQuestions(context: DraftGenerationContext) {
    const apiKey = process.env.AI_LITERACY_DEEPSEEK_API_KEY || process.env.DEEPSEEK_API_KEY;
    if (!apiKey) {
      throw new Error("AI_LITERACY_DEEPSEEK_API_KEY or DEEPSEEK_API_KEY is not configured");
    }

    const baseUrl = process.env.DEEPSEEK_BASE_URL ?? "https://api.deepseek.com";
    const model = process.env.DEEPSEEK_MODEL ?? "deepseek-chat";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model,
        messages: buildMessages(context),
        temperature: 0.4,
        response_format: { type: "json_object" }
      })
    });

    const result = (await response.json()) as DeepSeekResponse;
    if (!response.ok) {
      throw new Error(result.error?.message || `DeepSeek request failed with ${response.status}`);
    }

    const content = result.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error("DeepSeek response did not include content");
    }

    const parsed = JSON.parse(stripCodeFence(content)) as QuestionInput[] | { questions?: QuestionInput[] };
    return Array.isArray(parsed) ? parsed : parseQuestions(JSON.stringify(parsed.questions ?? []));
  }
};
