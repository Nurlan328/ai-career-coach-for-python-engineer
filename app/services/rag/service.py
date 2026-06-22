"""RAG answer orchestration: retrieve from the KB, then ground the LLM answer.

Offline (no API key) it still returns the retrieved snippets + sources, so the
endpoint is useful without Claude.
"""
import asyncio
import logging

from app.core.config import settings
from app.schemas.coach import RagSource
from app.services.ai_service import ai
from app.services.rag.index import rag_index

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a Python backend mentor answering strictly from the provided context. "
    "Use ONLY the context; cite sources inline as [n]. If the context does not "
    "contain the answer, say so honestly instead of inventing. "
    "Respond in the question's language (default: Russian)."
)


async def answer(
    question: str, history: list | None = None
) -> tuple[str, str, list[RagSource]]:
    """Return (answer, source, sources). source is 'ai' or 'offline'."""
    hits = await asyncio.to_thread(rag_index.search, question, settings.rag_top_k)

    sources = [
        RagSource(
            title=h["title"],
            source=h["source"],
            snippet=h["text"][:400],
            score=round(h["score"], 3),
        )
        for h in hits
    ]

    if not hits:
        return "В базе знаний ничего не найдено по этому вопросу.", "offline", []

    context = "\n\n".join(
        f"[{i + 1}] {h['title']} ({h['source']})\n{h['text']}"
        for i, h in enumerate(hits)
    )

    if ai.enabled:
        try:
            user = f"Context:\n{context}\n\nQuestion: {question}"
            text = await ai.complete_text(_SYSTEM, [{"role": "user", "content": user}])
            return text, "ai", sources
        except Exception:  # noqa: BLE001
            logger.exception("RAG generation failed; returning snippets")

    offline = "LLM выключен — релевантные фрагменты из базы знаний:\n\n" + "\n\n".join(
        f"[{i + 1}] {h['title']}: {h['text'][:300]}" for i, h in enumerate(hits)
    )
    return offline, "offline", sources
