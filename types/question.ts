export type QuestionStatus = "draft" | "reviewed" | "tested" | "retired";

export type CognitiveLevel =
  | "remember"
  | "understand"
  | "apply"
  | "analyze"
  | "evaluate"
  | "create";

export type DifficultyEstimate = "easy" | "medium" | "hard";

export type QuestionType =
  | "单选"
  | "多选"
  | "判断"
  | "填空"
  | "案例分析"
  | "情景任务"
  | "挑战任务"
  | "技术主观题"
  | "情境决策题"
  | "短答建构题"
  | "案例分析题"
  | "解释理由题"
  | "过程说明题"
  | "方案设计题"
  | "项目任务题"
  | string;

export interface QuestionOption {
  id: string;
  text: string;
}

export interface Question {
  id: string;
  itemCode: string;
  questionType?: QuestionType;
  title: string;
  question: string;
  scenario: string;
  options: QuestionOption[];
  correctAnswer: string;
  explanation: string;
  dimension: string;
  secondaryDimension: string;
  tertiaryDimension?: string;
  quaternaryDimension?: string;
  subSkill: string;
  cognitiveLevel: CognitiveLevel;
  difficultyEstimate: DifficultyEstimate;
  tags: string[];
  knowledgePoints?: string[];
  sourceReference: string;
  status: QuestionStatus;
  stage?: string;
  knowledgeCode?: string;
  primaryDimension?: string;
  tertiaryAbility?: string;
  knowledgePoint?: string;
  questionTask?: string;
  referenceAnswer?: string;
  scoringCriteria?: string;
  form?: string;
  scoreMax?: number | null;
  discrimination?: number | null;
  sourceSheet?: string;
  sourceRow?: number;
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

export interface KnowledgePoint {
  id: string;
  knowledgeCode: string;
  stage: string;
  primaryDimension: string;
  secondaryDimension: string;
  tertiaryAbility: string;
  knowledgePoint: string;
  description: string;
  cognitiveLevel: string;
  suggestedQuestionTypes: string[];
  sourceReferences: string[];
  tags: string[];
  status: string;
  sourceSheet: string;
  sourceRow: number;
  createdAt: string;
  updatedAt: string;
}
