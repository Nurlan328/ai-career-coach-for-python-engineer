"""Interview request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterviewStartRequest(BaseModel):
    category: str = Field(examples=["Async Python"])
    level: str = Field(default="middle", examples=["middle"])
    num_questions: int = Field(default=5, ge=1, le=20)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_index: int
    question_text: str
    category: str
    difficulty: str
    answered: bool = False


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    level: str
    category: str
    status: str
    total_score: float | None = None
    created_at: datetime
    questions: list[QuestionOut] = []


class AnswerRequest(BaseModel):
    question_id: int
    answer: str = Field(min_length=1)


class AnswerFeedback(BaseModel):
    """Evaluation result for a single answer."""

    score: float
    strengths: list[str] = []
    weaknesses: list[str] = []
    missing_topics: list[str] = []
    ideal_answer: str = ""


class AnswerResponse(BaseModel):
    question_id: int
    feedback: AnswerFeedback
    next_question: QuestionOut | None = None
    interview_completed: bool = False
    interview_total_score: float | None = None


class AnsweredQuestion(BaseModel):
    question_id: int
    question_text: str
    category: str
    difficulty: str
    user_answer: str | None = None
    score: float | None = None
    feedback: dict | None = None
    ideal_answer: str | None = None


class InterviewResult(BaseModel):
    interview_id: int
    category: str
    level: str
    status: str
    total_score: float | None = None
    answered_count: int
    total_questions: int
    questions: list[AnsweredQuestion]


class InterviewListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    level: str
    category: str
    status: str
    total_score: float | None = None
    created_at: datetime
