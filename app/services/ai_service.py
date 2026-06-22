"""Thin async wrapper around the Claude (Anthropic) API.

The wrapper is intentionally optional: if no ANTHROPIC_API_KEY is configured the
service reports ``enabled is False`` and callers fall back to deterministic logic,
so the whole API stays runnable without credentials.
"""
import json
import logging
from collections.abc import AsyncIterator

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover - anthropic not installed
    AsyncAnthropic = None


class AIService:
    def __init__(self) -> None:
        self._client = None
        if settings.anthropic_api_key and AsyncAnthropic is not None:
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> dict | list:
        """Send a prompt to Claude and parse a JSON object/array from the reply."""
        if not self.enabled:
            raise RuntimeError("AIService is disabled (no ANTHROPIC_API_KEY).")

        message = await self._client.messages.create(
            model=settings.llm_model,
            max_tokens=max_tokens or settings.llm_max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in message.content if block.type == "text"
        )
        return _extract_json(text)

    async def complete_text(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int | None = None,
    ) -> str:
        """Send a message list to Claude and return the raw text reply."""
        if not self.enabled:
            raise RuntimeError("AIService is disabled (no ANTHROPIC_API_KEY).")

        message = await self._client.messages.create(
            model=settings.llm_model,
            max_tokens=max_tokens or settings.llm_max_tokens,
            system=system,
            messages=messages,
        )
        return "".join(
            block.text for block in message.content if block.type == "text"
        ).strip()

    async def stream_text(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream Claude's reply as incremental text chunks."""
        if not self.enabled:
            raise RuntimeError("AIService is disabled (no ANTHROPIC_API_KEY).")

        async with self._client.messages.stream(
            model=settings.llm_model,
            max_tokens=max_tokens or settings.llm_max_tokens,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text


def _extract_json(text: str) -> dict | list:
    """Best-effort extraction of the first JSON object/array in a string."""
    text = text.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fences.
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("`").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to slicing between the outermost brackets.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not parse JSON from model output: {text[:200]!r}")


# Module-level singleton used by the domain services.
ai = AIService()
