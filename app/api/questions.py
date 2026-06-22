"""Question generation endpoints."""
from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.schemas.question import (
    LEVELS,
    QUESTION_CATEGORIES,
    QuestionGenerateRequest,
    QuestionGenerateResponse,
)
from app.services.question_service import generate_questions

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/categories")
async def list_categories() -> dict:
    return {"categories": QUESTION_CATEGORIES, "levels": LEVELS}


@router.post("/generate", response_model=QuestionGenerateResponse)
async def generate(
    payload: QuestionGenerateRequest, _current_user: CurrentUser
) -> QuestionGenerateResponse:
    questions, source = await generate_questions(
        category=payload.category, level=payload.level, count=payload.count
    )
    return QuestionGenerateResponse(
        category=payload.category,
        level=payload.level,
        source=source,
        questions=questions,
    )
