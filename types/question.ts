export type QuestionStatus = "draft" | "reviewed" | "tested" | "retired";

export type CognitiveLevel =
  | "remember"
  | "understand"
  | "apply"
  | "analyze"
  | "evaluate"
  | "create";

export type DifficultyEstimate = "easy" | "medium" | "hard";

export interface QuestionOption {
  id: string;
  text: string;
}

export interface Question {
  id: string;
  itemCode: string;
  title: string;
  question: string;
  scenario: string;
  options: QuestionOption[];
  correctAnswer: string;
  explanation: string;
  dimension: string;
  secondaryDimension: string;
  subSkill: string;
  cognitiveLevel: CognitiveLevel;
  difficultyEstimate: DifficultyEstimate;
  tags: string[];
  sourceReference: string;
  status: QuestionStatus;
  createdAt: string;
  updatedAt: string;
}

export type QuestionInput = Omit<Question, "id" | "itemCode" | "createdAt" | "updatedAt">;

export interface QuestionFilters {
  dimension?: string;
  secondaryDimension?: string;
  status?: QuestionStatus | "";
  difficulty?: DifficultyEstimate | "";
  tag?: string;
  search?: string;
}
