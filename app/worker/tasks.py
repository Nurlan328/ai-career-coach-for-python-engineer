"""Celery tasks. Heavy work (resume parsing + LLM analysis) runs off the request."""
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.resume import Resume
from app.services.resume_service import analyze_resume

logger = logging.getLogger(__name__)


@celery_app.task(name="process_resume")
def process_resume(resume_id: int) -> dict:
    """(Re)analyze a stored resume and persist the result. Sync entrypoint."""
    return asyncio.run(_process_resume(resume_id))


async def _process_resume(resume_id: int) -> dict:
    # Fresh engine per task run: avoids event-loop binding issues in the worker.
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with session_factory() as db:
            resume = await db.get(Resume, resume_id)
            if resume is None:
                return {"status": "not_found", "resume_id": resume_id}

            analysis = await analyze_resume(resume.parsed_text)
            resume.ai_summary = analysis.summary
            resume.detected_level = analysis.detected_level
            resume.skills = analysis.skills
            resume.strengths = analysis.strengths
            resume.weaknesses = analysis.weaknesses
            resume.recommendations = analysis.recommendations
            await db.commit()
            logger.info("Resume %s reanalyzed: level=%s", resume_id, analysis.detected_level)
            return {
                "status": "done",
                "resume_id": resume_id,
                "level": analysis.detected_level,
            }
    finally:
        await engine.dispose()
