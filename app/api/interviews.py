"""Mock interview endpoints: start, answer, result, history."""
from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.interview import (
    AnsweredQuestion,
    AnswerRequest,
    AnswerResponse,
    InterviewListItem,
    InterviewOut,
    InterviewResult,
    InterviewStartRequest,
    QuestionOut,
)
from app.services import billing, interview_service

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _question_out(question) -> QuestionOut:
    return QuestionOut(
        id=question.id,
        order_index=question.order_index,
        question_text=question.question_text,
        category=question.category,
        difficulty=question.difficulty,
        answered=question.answer is not None,
    )


@router.post("/start", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
async def start(
    payload: InterviewStartRequest, current_user: CurrentUser, db: DbSession
) -> InterviewOut:
    await billing.check_interview_quota(db, current_user)
    interview = await interview_service.start_interview(
        db,
        user_id=current_user.id,
        category=payload.category,
        level=payload.level,
        num_questions=payload.num_questions,
    )
    return InterviewOut(
        id=interview.id,
        type=interview.type,
        level=interview.level,
        category=interview.category,
        status=interview.status,
        total_score=interview.total_score,
        created_at=interview.created_at,
        questions=[_question_out(q) for q in interview.questions],
    )


@router.get("/history", response_model=list[InterviewListItem])
async def history(current_user: CurrentUser, db: DbSession):
    return await interview_service.list_interviews(db, current_user.id)


@router.post("/{interview_id}/answer", response_model=AnswerResponse)
async def answer(
    interview_id: int,
    payload: AnswerRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AnswerResponse:
    interview = await interview_service.get_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    questions = {q.id: q for q in interview.questions}
    question = questions.get(payload.question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question does not belong to this interview",
        )

    feedback = await interview_service.submit_answer(db, question, payload.answer)
    interview = await interview_service.maybe_finalize(db, interview_id)

    # Reload to compute the next unanswered question.
    interview = await interview_service.get_interview(db, interview_id, current_user.id)
    next_q = next(
        (q for q in interview.questions if q.answer is None),
        None,
    )

    return AnswerResponse(
        question_id=question.id,
        feedback=feedback,
        next_question=_question_out(next_q) if next_q else None,
        interview_completed=interview.status == "completed",
        interview_total_score=interview.total_score,
    )


@router.get("/{interview_id}/result", response_model=InterviewResult)
async def result(
    interview_id: int, current_user: CurrentUser, db: DbSession
) -> InterviewResult:
    interview = await interview_service.get_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    answered = 0
    questions: list[AnsweredQuestion] = []
    for q in interview.questions:
        a = q.answer
        if a is not None:
            answered += 1
        questions.append(
            AnsweredQuestion(
                question_id=q.id,
                question_text=q.question_text,
                category=q.category,
                difficulty=q.difficulty,
                user_answer=a.user_answer if a else None,
                score=a.score if a else None,
                feedback=a.ai_feedback if a else None,
                ideal_answer=(a.ideal_answer if a else None) or q.expected_answer,
            )
        )

    return InterviewResult(
        interview_id=interview.id,
        category=interview.category,
        level=interview.level,
        status=interview.status,
        total_score=interview.total_score,
        answered_count=answered,
        total_questions=len(interview.questions),
        questions=questions,
    )
