import { buildDraftPrompt } from "@/lib/llm/prompts";
import { aiLiteracyDimensions, aiLiteracySecondaryDimensions } from "@/lib/aiLiteracyFramework";
import { DraftGenerationContext, DraftQuestionProvider } from "@/lib/llm/types";
import { QuestionInput } from "@/types/question";

type OpenAIContentItem = {
  type?: string;
  text?: string;
};

type OpenAIResponse = {
  output_text?: string;
  output?: Array<{
    content?: OpenAIContentItem[];
  }>;
  error?: {
    message?: string;
  };
};

const questionDraftSchema = {
  type: "object",
  additionalProperties: false,
  required: ["questions"],
  properties: {
    questions: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: [
          "title",
          "question",
          "scenario",
          "options",
          "correctAnswer",
          "explanation",
          "dimension",
          "secondaryDimension",
          "subSkill",
          "cognitiveLevel",
          "difficultyEstimate",
          "tags",
          "sourceReference",
          "status"
        ],
        properties: {
          title: { type: "string" },
          question: { type: "string" },
          scenario: { type: "string" },
          options: {
            type: "array",
            items: {
              type: "object",
              additionalProperties: false,
              required: ["id", "text"],
              properties: {
                id: { type: "string", enum: ["A", "B", "C", "D"] },
                text: { type: "string" }
              }
            }
          },
          correctAnswer: { type: "string", enum: ["A", "B", "C", "D"] },
          explanation: { type: "string" },
          dimension: { type: "string", enum: aiLiteracyDimensions },
          secondaryDimension: { type: "string", enum: aiLiteracySecondaryDimensions },
          subSkill: { type: "string" },
          cognitiveLevel: {
            type: "string",
            enum: ["remember", "understand", "apply", "analyze", "evaluate", "create"]
          },
          difficultyEstimate: { type: "string", enum: ["easy", "medium", "hard"] },
          tags: {
            type: "array",
            items: { type: "string" }
          },
          sourceReference: { type: "string" },
          status: { type: "string", enum: ["draft"] }
        }
      }
    }
  }
} as const;

function extractOutputText(result: OpenAIResponse) {
  if (result.output_text) {
    return result.output_text;
  }

  return (
    result.output
      ?.flatMap((item) => item.content ?? [])
      .map((content) => content.text)
      .filter((text): text is string => Boolean(text))
      .join("\n")
      .trim() ?? ""
  );
}

function parseQuestions(content: string) {
  const parsed = JSON.parse(content) as { questions?: QuestionInput[] };
  if (!Array.isArray(parsed.questions)) {
    throw new Error("OpenAI response must include a questions array");
  }

  return parsed.questions;
}

export const openaiProvider: DraftQuestionProvider = {
  async generateDraftQuestions(context: DraftGenerationContext) {
    const apiKey = process.env.AI_LITERACY_OPENAI_API_KEY || process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error("AI_LITERACY_OPENAI_API_KEY or OPENAI_API_KEY is not configured");
    }

    const baseUrl = process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1";
    const model = process.env.OPENAI_MODEL ?? "gpt-5.5";
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/responses`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model,
        input: [
          {
            role: "system",
            content:
              "You are an AI literacy assessment item writer. Return only valid JSON that matches the schema. Generate Chinese scenario-based single-choice draft questions."
          },
          {
            role: "user",
            content: buildDraftPrompt(context)
          }
        ],
        text: {
          format: {
            type: "json_schema",
            name: "ai_literacy_question_drafts",
            schema: questionDraftSchema,
            strict: true
          }
        }
      })
    });

    const result = (await response.json()) as OpenAIResponse;
    if (!response.ok) {
      throw new Error(result.error?.message || `OpenAI request failed with ${response.status}`);
    }

    const content = extractOutputText(result);
    if (!content) {
      throw new Error("OpenAI response did not include output text");
    }

    return parseQuestions(content);
  }
};
