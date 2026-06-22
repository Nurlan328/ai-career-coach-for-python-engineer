"""Resume endpoints: upload + analyze, fetch analysis, list, background reanalyze."""
import asyncio

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models.resume import Resume
from app.schemas.resume import ResumeListItem, ResumeOut
from app.services.resume_service import analyze_resume
from app.utils.file_parser import UnsupportedFileType, extract_text
from app.worker.tasks import process_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> Resume:
    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_mb} MB limit",
        )

    try:
        text = extract_text(file.filename or "resume", content)
    except UnsupportedFileType as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any text from the file",
        )

    analysis = await analyze_resume(text)

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename or "resume",
        parsed_text=text,
        ai_summary=analysis.summary,
        detected_level=analysis.detected_level,
        skills=analysis.skills,
        strengths=analysis.strengths,
        weaknesses=analysis.weaknesses,
        recommendations=analysis.recommendations,
    )
    db.add(resume)

    # Keep the user's level in sync with their latest resume.
    current_user.level = analysis.detected_level
    db.add(current_user)

    await db.commit()
    await db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeListItem])
async def list_resumes(current_user: CurrentUser, db: DbSession) -> list[Resume]:
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{resume_id}/analysis", response_model=ResumeOut)
async def get_resume_analysis(
    resume_id: int, current_user: CurrentUser, db: DbSession
) -> Resume:
    resume = await db.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


@router.post("/{resume_id}/reanalyze", status_code=status.HTTP_202_ACCEPTED)
async def reanalyze_resume(
    resume_id: int, current_user: CurrentUser, db: DbSession
) -> dict:
    """Re-run analysis in the background via Celery (heavy LLM work off-request)."""
    resume = await db.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    if settings.celery_task_always_eager:
        # Run inline (in a worker thread to avoid a nested event loop).
        await asyncio.to_thread(process_resume.apply, args=[resume_id])
        return {"resume_id": resume_id, "status": "done"}

    result = process_resume.delay(resume_id)
    return {"resume_id": resume_id, "task_id": result.id, "status": "queued"}
