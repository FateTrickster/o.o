import { buildDraftPrompt } from "@/lib/llm/prompts";
import { normalizeFrameworkSelection } from "@/lib/aiLiteracyFramework";
import { DraftGenerationContext, DraftQuestionProvider } from "@/lib/llm/types";
import { QuestionInput } from "@/types/question";

type XfyunMessage = {
  role: "system" | "user";
  content: string;
};

type XfyunResponse = {
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
  const cleaned = stripCodeFence(content);
  const parsed = JSON.parse(cleaned) as QuestionInput[] | { questions?: QuestionInput[] };
  const questions = Array.isArray(parsed) ? parsed : parsed.questions;

  if (!Array.isArray(questions)) {
    throw new Error("Xfyun MaaS response must include a questions array");
  }

  return questions.map((question) => ({
    ...question,
    ...normalizeFrameworkSelection(
      question.dimension,
      question.secondaryDimension,
      `${question.title} ${question.question} ${question.scenario} ${question.subSkill} ${question.tags?.join(" ")}`
    )
  }));
}

function buildMessages(context: DraftGenerationContext): XfyunMessage[] {
  return [
    {
      role: "system",
      content:
        "你是 AI 素养测评题库出题助手。只输出合法 JSON，不要输出 Markdown。JSON 格式必须是 {\"questions\":[...]}。"
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

export const xfyunProvider: DraftQuestionProvider = {
  async generateDraftQuestions(context: DraftGenerationContext) {
    const apiKey = process.env.XFYUN_MAAS_API_KEY;
    if (!apiKey) {
      throw new Error("XFYUN_MAAS_API_KEY is not configured");
    }

    const baseUrl = process.env.XFYUN_MAAS_BASE_URL ?? "https://maas-api.cn-huabei-1.xf-yun.com/v2";
    const model = process.env.XFYUN_MAAS_MODEL ?? "Qwen3.6-35B-A3B";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model,
        messages: buildMessages(context),
        temperature: 0.4
      })
    });

    const result = (await response.json()) as XfyunResponse;
    if (!response.ok) {
      throw new Error(result.error?.message || `Xfyun MaaS request failed with ${response.status}`);
    }

    const content = result.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error("Xfyun MaaS response did not include content");
    }

    return parseQuestions(content);
  }
};
