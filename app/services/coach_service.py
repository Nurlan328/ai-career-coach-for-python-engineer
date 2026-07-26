"""Free-form Python backend tutor: answers any question via Claude.

Supports multi-turn context (follow-up questions) and token streaming. Unlike the
question/resume/evaluation services there is no meaningful offline fallback for
open-ended Q&A, so without an API key this returns an explicit 'unavailable'
response instead of a fabricated answer.
"""
import logging
from collections.abc import AsyncIterator

from app.core.config import settings
from app.schemas.coach import ChatTurn
from app.services.ai_service import ai

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a senior Python backend engineering mentor. "
    "Answer the user's question clearly, accurately and practically, with short "
    "code examples when they help and production trade-offs in mind. "
    "If the question is unrelated to Python or backend engineering, briefly say so "
    "and steer the user back to relevant topics. "
    "Respond in the same language as the question (default: Russian)."
)

_UNAVAILABLE = (
    "AI-ответы недоступны: не задан ANTHROPIC_API_KEY. "
    "Добавьте ключ в .env, чтобы получать ответы от Claude."
)


def _build_messages(
    question: str, category: str | None, history: list[ChatTurn]
) -> list[dict]:
    """Build a valid Anthropic message list from history + the new question.

    Anthropic requires messages to start with a 'user' turn and alternate roles,
    so we merge consecutive same-role turns and drop any leading assistant turns.
    """
    raw = [{"role": t.role, "content": t.content} for t in history]
    user = question if not category else f"[Тема: {category}]\n{question}"
    raw.append({"role": "user", "content": user})

    norm: list[dict] = []
    for msg in raw:
        if norm and norm[-1]["role"] == msg["role"]:
            norm[-1]["content"] += "\n\n" + msg["content"]
        else:
            norm.append(dict(msg))
    while norm and norm[0]["role"] != "user":
        norm.pop(0)
    return norm


async def ask(
    question: str, category: str | None = None, history: list[ChatTurn] | None = None
) -> tuple[str, str, str | None]:
    """Return (answer, source, model)."""
    if not ai.enabled:
        return _UNAVAILABLE, "unavailable", None

    messages = _build_messages(question, category, history or [])
    try:
        answer = await ai.complete_text(_SYSTEM, messages)
        return answer, "ai", settings.llm_model
    except Exception:  # noqa: BLE001
        logger.exception("Coach LLM call failed")
        return "Не удалось получить ответ от модели. Попробуйте позже.", "error", None


async def ask_stream(
    question: str, category: str | None = None, history: list[ChatTurn] | None = None
) -> AsyncIterator[str]:
    """Yield the answer as incremental text chunks."""
    if not ai.enabled:
        yield _UNAVAILABLE
        return

    messages = _build_messages(question, category, history or [])
    try:
        async for chunk in ai.stream_text(_SYSTEM, messages):
            yield chunk
    except Exception:  # noqa: BLE001
        logger.exception("Coach streaming failed")
        yield "\n[Ошибка: не удалось получить ответ от модели.]"
