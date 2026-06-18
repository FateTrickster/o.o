from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    id: str
    text: str


class QuestionInput(BaseModel):
    questionType: str = "单选"
    title: str
    question: str
    scenario: str
    options: List[QuestionOption]
    correctAnswer: str
    explanation: str
    dimension: str
    secondaryDimension: str
    tertiaryDimension: str = ""
    quaternaryDimension: str = ""
    subSkill: str
    cognitiveLevel: str
    difficultyEstimate: str
    tags: List[str] = Field(default_factory=list)
    knowledgePoints: List[str] = Field(default_factory=list)
    sourceReference: str
    status: str = "draft"
    stage: str = ""
    knowledgeCode: str = ""
    primaryDimension: str = ""
    tertiaryAbility: str = ""
    knowledgePoint: str = ""
    questionTask: str = ""
    referenceAnswer: str = ""
    scoringCriteria: str = ""
    form: str = ""
    scoreMax: Optional[float] = None
    discrimination: Optional[float] = None
    sourceSheet: str = ""
    sourceRow: int = 0


class Question(QuestionInput):
    id: str
    itemCode: str
    createdAt: str
    updatedAt: str


class KnowledgeEntry(BaseModel):
    id: str
    title: str
    content: str
    sourceFileName: str = ""
    sourceType: str = ""
    tags: List[str] = Field(default_factory=list)
    createdAt: str
    updatedAt: str


class KnowledgeInput(BaseModel):
    title: str
    content: str
    sourceFileName: str = ""
    sourceType: str = ""
    tags: List[str] = Field(default_factory=list)


class QuestionDraft(QuestionInput):
    id: str
    sourceKnowledgeIds: List[str] = Field(default_factory=list)
    generationRequirement: str = ""
    generationJobId: Optional[str] = None
    createdAt: str
    updatedAt: str


class GenerateDraftRequest(BaseModel):
    knowledgeIds: List[str]
    requirement: str = ""
    targetDimensions: List[str] = Field(default_factory=list)
    targetSecondaryDimensions: List[str] = Field(default_factory=list)
    targetTags: List[str] = Field(default_factory=list)
    count: int = Field(default=3, ge=1, le=20)
    provider: Optional[str] = None
    model: Optional[str] = None


class GenerationJob(BaseModel):
    id: str
    provider: str
    model: str
    requirement: str
    targetDimensions: List[str] = Field(default_factory=list)
    targetSecondaryDimensions: List[str] = Field(default_factory=list)
    targetTags: List[str] = Field(default_factory=list)
    count: int
    status: str
    createdAt: str
    completedAt: Optional[str] = None
    error: Optional[str] = None
    draftCount: int = 0
    batchCount: int = 0
    completedBatchCount: int = 0
    failedBatchCount: int = 0


class GenerationBatch(BaseModel):
    id: str
    jobId: str
    batchIndex: int
    provider: str
    model: str
    plannedCount: int
    generatedCount: int = 0
    status: str
    startedAt: str
    completedAt: Optional[str] = None
    error: Optional[str] = None


class QuestionType(BaseModel):
    id: str
    name: str
    description: str = ""
    sourceSheet: str = ""
    exampleCount: int = 0
    createdAt: str
    updatedAt: str


class QuestionTypeExample(BaseModel):
    id: str
    questionType: str
    question: str
    task: str = ""
    referenceAnswer: str = ""
    scoringCriteria: str = ""
    knowledgePointRaw: str = ""
    sourceReference: str = ""
    sourceSheet: str = ""
    sourceRow: int = 0
    createdAt: str
    updatedAt: str


class KnowledgeTaxonomyItem(BaseModel):
    id: str
    gradeLevel: str = ""
    primaryDimension: str = ""
    secondaryDimension: str = ""
    tertiaryDimension: str = ""
    quaternaryDimension: str = ""
    knowledgePoint: str = ""
    knowledgeDescription: str = ""
    sourceReference: str = ""
    note: str = ""
    sourceSheet: str = ""
    sourceRow: int = 0
    createdAt: str
    updatedAt: str


class KnowledgePoint(BaseModel):
    id: str
    knowledgeCode: str
    stage: str = ""
    primaryDimension: str = ""
    secondaryDimension: str = ""
    tertiaryAbility: str = ""
    knowledgePoint: str = ""
    description: str = ""
    cognitiveLevel: str = ""
    suggestedQuestionTypes: List[str] = Field(default_factory=list)
    sourceReferences: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    status: str = "active"
    sourceSheet: str = ""
    sourceRow: int = 0
    createdAt: str
    updatedAt: str


class ImportJsonRequest(BaseModel):
    reset: bool = False


class ImportQuestionsResult(BaseModel):
    imported: int
    total: int


class ImportKnowledgeResult(BaseModel):
    imported: int
    total: int


class ApiError(BaseModel):
    error: str


JsonDict = Dict[str, Any]
