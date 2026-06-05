import { DraftGenerationContext, DraftQuestionProvider } from "@/lib/llm/types";
import { QuestionInput } from "@/types/question";

function compactText(text: string, length = 90) {
  return text.replace(/\s+/g, " ").trim().slice(0, length);
}

export const mockProvider: DraftQuestionProvider = {
  async generateDraftQuestions(context: DraftGenerationContext): Promise<QuestionInput[]> {
    const count = context.count ?? 3;
    const entries = context.knowledgeEntries;

    return Array.from({ length: count }, (_, index) => {
      const entry = entries[index % entries.length];
      const stem = compactText(entry.content, 80) || entry.title;
      const requirement = compactText(context.requirement, 40) || "AI素养应用";

      return {
        title: `${entry.title} 场景题 ${index + 1}`,
        question: `在以下场景中，最符合“${requirement}”要求的做法是什么？`,
        scenario: `学习者正在处理与“${entry.title}”相关的问题。参考知识点：${stem}`,
        options: [
          { id: "A", text: "先核对信息来源和适用条件，再决定如何使用 AI 工具" },
          { id: "B", text: "直接相信 AI 输出，因为它通常比人工判断更稳定" },
          { id: "C", text: "只关注生成速度，不需要检查结果是否符合场景" },
          { id: "D", text: "把所有原始敏感信息完整输入 AI，以便得到更详细答案" }
        ],
        correctAnswer: "A",
        explanation: "AI 素养强调结合场景、来源、约束和风险进行判断。应先核验信息和适用条件，再使用或采纳 AI 输出。",
        dimension: "应用AI（Apply）",
        secondaryDimension: "能对AI生成结果的准确性和合理性进行判断",
        subSkill: "场景化判断",
        cognitiveLevel: index % 2 === 0 ? "apply" : "analyze",
        difficultyEstimate: index % 2 === 0 ? "medium" : "hard",
        tags: ["mock生成", entry.sourceType, ...entry.tags.slice(0, 2)].filter(Boolean),
        sourceReference: entry.sourceFileName || entry.title,
        status: "draft"
      };
    });
  }
};
