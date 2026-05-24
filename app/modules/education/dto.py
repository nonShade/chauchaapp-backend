"""
Education module DTOs.

Handles data transfer formatting for endpoints in the Education module.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModuleCardDTO(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    level: str
    estimatedTimeMinutes: int
    topicsCount: int
    questionsCount: int
    category: str
    tags: list[str]


class SectionDTO(BaseModel):
    id: str
    title: str
    content: str
    source: dict | None = None


class ContentDTO(BaseModel):
    introduction: str
    sections: list[SectionDTO]
    practicalTips: list[str]


class TopicDTO(BaseModel):
    id: str
    name: str


class QuestionDTO(BaseModel):
    id: str
    type: str
    question: str
    options: list[str] | None = None
    explanation: str | None = None
    correctAnswer: int | None = None


class QuizDTO(BaseModel):
    id: str
    title: str
    questionsCount: int
    passingScore: int
    questions: list[QuestionDTO]


class QuizAttemptDTO(BaseModel):
    attempt: int
    score: int
    correctAnswers: int
    totalQuestions: int
    completedAt: datetime


class UserModuleProgressDTO(BaseModel):
    userId: str
    moduleId: str
    status: str
    progressPercentage: int
    completedSections: list[str]
    quizAttempts: list[QuizAttemptDTO]
    startedAt: datetime | None = None
    lastAccessedAt: datetime | None = None
    completedAt: datetime | None = None


class StartModuleProgressResponseDTO(BaseModel):
    progress: UserModuleProgressDTO


class UpdateModuleProgressRequestDTO(BaseModel):
    sectionId: str = Field(..., min_length=1)


class SubmitQuizAttemptRequestDTO(BaseModel):
    score: int = Field(..., ge=0, le=100)
    correctAnswers: int = Field(..., ge=0)
    totalQuestions: int = Field(..., ge=1)


class SubmitQuizAttemptResponseDTO(BaseModel):
    passed: bool
    progress: UserModuleProgressDTO


class ModuleDetailDTO(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    level: str
    estimatedTimeMinutes: int
    topicsCount: int
    category: str
    tags: list[str]
    createdAt: datetime
    learningObjectives: list[str]
    content: ContentDTO
    topics: list[TopicDTO]
    quiz: QuizDTO


class ModuleDetailResponseDTO(BaseModel):
    module: ModuleDetailDTO
    progress: UserModuleProgressDTO


class ModuleWithProgressDTO(BaseModel):
    module: ModuleDetailDTO
    progress: UserModuleProgressDTO


class GenerateModulesResponseDTO(BaseModel):
    items: list[ModuleWithProgressDTO]


class ModulesListResponseDTO(BaseModel):
    totalCount: int
    modules: list[ModuleCardDTO]


class GenerateModuleItemDTO(BaseModel):
    topic: str = Field(..., min_length=3)
    level: str = Field(..., pattern="^(Principiante|Intermedio|Avanzado)$")


class GenerateModulesRequestDTO(BaseModel):
    items: list[GenerateModuleItemDTO] = Field(..., min_length=1)
