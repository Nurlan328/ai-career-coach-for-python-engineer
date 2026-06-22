"""Orchestrates the mock-interview lifecycle over the database."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interview import Interview, InterviewAnswer, InterviewQuestion
from app.schemas.interview import AnswerFeedback
from app.services import evaluation_service, question_service


async def start_interview(
    db: AsyncSession, user_id: int, category: str, level: str, num_questions: int
) -> Interview:
    generated, _source = await question_service.generate_questions(
        category=category, level=level, count=num_questions
    )

    interview = Interview(
        user_id=user_id,
        type="mock",
        level=level,
        category=category,
        status="in_progress",
        questions=[
            InterviewQuestion(
                order_index=i,
                question_text=q.question_text,
                category=q.category,
                difficulty=q.difficulty,
                expected_answer=q.expected_answer,
            )
            for i, q in enumerate(generated)
        ],
    )
    db.add(interview)
    await db.commit()

    return await get_interview(db, interview.id, user_id)


async def get_interview(
    db: AsyncSession, interview_id: int, user_id: int
) -> Interview | None:
    result = await db.execute(
        select(Interview)
        .where(Interview.id == interview_id, Interview.user_id == user_id)
        .options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer)
        )
    )
    return result.scalar_one_or_none()


async def list_interviews(db: AsyncSession, user_id: int) -> list[Interview]:
    result = await db.execute(
        select(Interview)
        .where(Interview.user_id == user_id)
        .order_by(Interview.created_at.desc())
    )
    return list(result.scalars().all())


async def submit_answer(
    db: AsyncSession, question: InterviewQuestion, answer_text: str
) -> AnswerFeedback:
    feedback = await evaluation_service.evaluate_answer(
        category=question.category,
        question=question.question_text,
        answer=answer_text,
    )

    answer = question.answer or InterviewAnswer()
    answer.user_answer = answer_text
    answer.score = feedback.score
    answer.ai_feedback = {
        "strengths": feedback.strengths,
        "weaknesses": feedback.weaknesses,
        "missing_topics": feedback.missing_topics,
    }
    answer.ideal_answer = feedback.ideal_answer or question.expected_answer
    # Link the relationship (not just the FK) so `question.answer` is refreshed in
    # the current session — otherwise the "next unanswered question" lookup that
    # follows in the same request still sees this question as unanswered.
    answer.question = question
    db.add(answer)
    await db.commit()
    return feedback


async def maybe_finalize(db: AsyncSession, interview_id: int) -> Interview:
    """Recompute progress; mark completed and set total_score if fully answered."""
    interview = await db.get(Interview, interview_id)

    total_q = await db.scalar(
        select(func.count(InterviewQuestion.id)).where(
            InterviewQuestion.interview_id == interview_id
        )
    )
    answered = await db.scalar(
        select(func.count(InterviewAnswer.id))
        .join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview_id)
    )

    if total_q and answered >= total_q:
        avg = await db.scalar(
            select(func.avg(InterviewAnswer.score))
            .join(
                InterviewQuestion,
                InterviewAnswer.question_id == InterviewQuestion.id,
            )
            .where(InterviewQuestion.interview_id == interview_id)
        )
        interview.status = "completed"
        interview.total_score = round(float(avg), 2) if avg is not None else None
        await db.commit()

    return interview
