"""Free-form Python tutor endpoint: ask Claude any backend question."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.cache import cache
from app.core.deps import CurrentUser
from app.schemas.coach import AskRequest, AskResponse, RagResponse
from app.services import coach_service
from app.services.rag import service as rag_service

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest, _current_user: CurrentUser) -> AskResponse:
    answer, source, model = await coach_service.ask(
        payload.question, payload.category, payload.history
    )
    return AskResponse(
        question=payload.question, answer=answer, source=source, model=model
    )


@router.post("/rag", response_model=RagResponse)
async def ask_rag(payload: AskRequest, _current_user: CurrentUser) -> RagResponse:
    """Answer grounded in the curated knowledge base, with cited sources."""
    # Cache single-shot questions (no conversation context) by normalized text.
    cache_key = None
    if not payload.history:
        cache_key = "rag:" + payload.question.strip().lower()
        cached = cache.get(cache_key)
        if cached is not None:
            return RagResponse(**cached)

    answer, source, sources = await rag_service.answer(payload.question, payload.history)
    response = RagResponse(
        question=payload.question, answer=answer, source=source, sources=sources
    )
    if cache_key is not None:
        cache.set(cache_key, response.model_dump())
    return response


@router.post("/ask/stream")
async def ask_question_stream(
    payload: AskRequest, _current_user: CurrentUser
) -> StreamingResponse:
    """Stream the answer token-by-token as plain text (text/plain)."""
    generator = coach_service.ask_stream(
        payload.question, payload.category, payload.history
    )
    return StreamingResponse(generator, media_type="text/plain; charset=utf-8")
