import { deepseekProvider } from "@/lib/llm/deepseekProvider";
import { kimiProvider } from "@/lib/llm/kimiProvider";
import { mockProvider } from "@/lib/llm/mockProvider";
import { openaiProvider } from "@/lib/llm/openaiProvider";
import { DraftGenerationContext } from "@/lib/llm/types";
import { xfyunProvider } from "@/lib/llm/xfyunProvider";

export async function generateDraftQuestions(context: DraftGenerationContext) {
  const provider = process.env.LLM_PROVIDER ?? "mock";

  if (provider === "openai") {
    return openaiProvider.generateDraftQuestions(context);
  }

  if (provider === "deepseek") {
    return deepseekProvider.generateDraftQuestions(context);
  }

  if (provider === "kimi") {
    return kimiProvider.generateDraftQuestions(context);
  }

  if (provider === "xfyun") {
    return xfyunProvider.generateDraftQuestions(context);
  }

  if (provider !== "mock") {
    throw new Error(`Unsupported LLM_PROVIDER "${provider}". Use "mock", "openai", "deepseek", "kimi", or "xfyun".`);
  }

  return mockProvider.generateDraftQuestions(context);
}
