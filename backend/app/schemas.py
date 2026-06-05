from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    id: str
    text: str


class QuestionInput(BaseModel):
    title: str
    question: str
    scenario: str
    options: List[QuestionOption]
    correctAnswer: str
    explanation: str
    dimension: str
    secondaryDimension: str
    subSkill: str
    cognitiveLevel: str
    difficultyEstimate: str
    tags: List[str] = Field(default_factory=list)
    sourceReference: str
    status: str = "draft"


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
    count: int = 3
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


class ImportJsonRequest(BaseModel):
    reset: bool = False


class ApiError(BaseModel):
    error: str


JsonDict = Dict[str, Any]
