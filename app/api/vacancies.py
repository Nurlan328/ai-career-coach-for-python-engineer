"""Vacancy endpoints: analyze a posting, gap-analysis vs a resume, prep roadmap."""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.resume import Resume
from app.models.vacancy import Vacancy
from app.schemas.vacancy import (
    CompareRequest,
    GapAnalysis,
    Roadmap,
    RoadmapRequest,
    VacancyAnalyzeRequest,
    VacancyListItem,
    VacancyOut,
)
from app.services import vacancy_service

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


async def _get_owned_vacancy(db: DbSession, user_id: int, vacancy_id: int) -> Vacancy:
    vacancy = await db.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")
    return vacancy


async def _get_owned_resume(db: DbSession, user_id: int, resume_id: int) -> Resume:
    resume = await db.get(Resume, resume_id)
    if resume is None or resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


@router.post("/analyze", response_model=VacancyOut, status_code=status.HTTP_201_CREATED)
async def analyze(
    payload: VacancyAnalyzeRequest, current_user: CurrentUser, db: DbSession
) -> Vacancy:
    analysis = await vacancy_service.analyze_vacancy(payload.description)
    vacancy = Vacancy(
        user_id=current_user.id,
        title=payload.title,
        company=payload.company,
        description=payload.description,
        required_skills=analysis.required_skills,
        ai_summary=analysis.summary,
    )
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)
    return vacancy


@router.get("", response_model=list[VacancyListItem])
async def list_vacancies(current_user: CurrentUser, db: DbSession) -> list[Vacancy]:
    result = await db.execute(
        select(Vacancy)
        .where(Vacancy.user_id == current_user.id)
        .order_by(Vacancy.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/compare-with-resume", response_model=GapAnalysis)
async def compare_with_resume(
    payload: CompareRequest, current_user: CurrentUser, db: DbSession
) -> GapAnalysis:
    vacancy = await _get_owned_vacancy(db, current_user.id, payload.vacancy_id)
    resume = await _get_owned_resume(db, current_user.id, payload.resume_id)
    return await vacancy_service.compare(
        resume_skills=resume.skills or [],
        vacancy_skills=vacancy.required_skills or [],
        vacancy_description=vacancy.description,
    )


@router.post("/roadmap", response_model=Roadmap)
async def roadmap(
    payload: RoadmapRequest, current_user: CurrentUser, db: DbSession
) -> Roadmap:
    vacancy = await _get_owned_vacancy(db, current_user.id, payload.vacancy_id)
    resume = await _get_owned_resume(db, current_user.id, payload.resume_id)
    gap = await vacancy_service.compare(
        resume_skills=resume.skills or [],
        vacancy_skills=vacancy.required_skills or [],
        vacancy_description=vacancy.description,
    )
    return await vacancy_service.generate_roadmap(
        topics=gap.topics_to_study,
        level=resume.detected_level or "middle",
        weeks=payload.weeks,
    )
