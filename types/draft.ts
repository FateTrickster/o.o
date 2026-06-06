import { QuestionInput } from "@/types/question";

export interface QuestionDraft extends QuestionInput {
  id: string;
  sourceKnowledgeIds: string[];
  generationRequirement: string;
  generationJobId?: string | null;
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
  count?: number;
}

export interface GenerationJob {
  id: string;
  provider: string;
  model: string;
  requirement: string;
  targetDimensions: string[];
  targetSecondaryDimensions: string[];
  targetTags: string[];
  count: number;
  status: "running" | "completed" | "failed" | string;
  createdAt: string;
  completedAt?: string | null;
  error?: string | null;
  draftCount: number;
}
