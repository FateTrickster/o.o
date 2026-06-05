import { QuestionInput } from "@/types/question";

export interface QuestionDraft extends QuestionInput {
  id: string;
  sourceKnowledgeIds: string[];
  generationRequirement: string;
  createdAt: string;
  updatedAt: string;
}

export type QuestionDraftInput = Omit<QuestionDraft, "id" | "createdAt" | "updatedAt">;

export interface DraftGenerationRequest {
  knowledgeIds: string[];
  requirement: string;
  targetDimensions?: string[];
  targetSecondaryDimensions?: string[];
  targetTags?: string[];
}
