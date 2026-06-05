import { KnowledgeEntry } from "@/types/knowledge";
import { QuestionInput } from "@/types/question";

export interface DraftGenerationContext {
  knowledgeEntries: KnowledgeEntry[];
  requirement: string;
  targetDimensions?: string[];
  targetSecondaryDimensions?: string[];
  targetTags?: string[];
  count?: number;
}

export interface DraftQuestionProvider {
  generateDraftQuestions(context: DraftGenerationContext): Promise<QuestionInput[]>;
}
