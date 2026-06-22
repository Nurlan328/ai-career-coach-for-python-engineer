"""Question generation schemas."""
from pydantic import BaseModel, Field

# Categories supported by the question generator (from the project spec).
QUESTION_CATEGORIES = [
    "Python Core",
    "OOP in Python",
    "Async Python",
    "FastAPI",
    "Django",
    "Flask",
    "SQLAlchemy",
    "PostgreSQL",
    "Redis",
    "Celery",
    "Docker",
    "System Design",
    "Testing",
    "Algorithms",
]

LEVELS = ["junior", "middle", "senior"]


class QuestionGenerateRequest(BaseModel):
    category: str = Field(examples=["Async Python"])
    level: str = Field(default="middle", examples=["middle"])
    count: int = Field(default=5, ge=1, le=20)


class GeneratedQuestion(BaseModel):
    question_text: str
    category: str
    difficulty: str
    expected_answer: str | None = None


class QuestionGenerateResponse(BaseModel):
    category: str
    level: str
    source: str  # "ai" or "bank"
    questions: list[GeneratedQuestion]
