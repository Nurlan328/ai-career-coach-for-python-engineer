"""Thin async wrapper around the LLM provider (Claude or local Ollama).

The wrapper is intentionally optional: if no provider is configured the service
reports ``enabled is False`` and callers fall back to deterministic logic, so
the whole API stays runnable without credentials.

Providers (see settings.llm_provider):
  - "auto" (default): Claude when ANTHROPIC_API_KEY is set, otherwise disabled.
  - "anthropic": Claude explicitly.
  - "ollama": a free local model served by Ollama (settings.ollama_*).
"""
import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover - anthropic not installed
    anthropic = None
    AsyncAnthropic = None

_OLLAMA_TIMEOUT = httpx.Timeout(connect=5.0, read=300.0, write=30.0, pool=5.0)


class AIService:
    def __init__(self) -> None:
        self._client = None
        self._provider: str | None = None

        provider = settings.llm_provider.lower()
        if provider == "ollama":
            self._provider = "ollama"
        elif provider in ("auto", "anthropic"):
            if settings.anthropic_api_key and AsyncAnthropic is not None:
                self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
                self._provider = "anthropic"

    @property
    def enabled(self) -> bool:
        return self._provider is not None

    @property
    def provider(self) -> str | None:
        return self._provider

    @property
    def model_name(self) -> str | None:
        if self._provider == "ollama":
            return settings.ollama_model
        if self._provider == "anthropic":
            return settings.llm_model
        return None

    async def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> dict | list:
        """Send a prompt to the model and parse a JSON object/array from the reply."""
        text = await self.complete_text(system, [{"role": "user", "content": user}], max_tokens)
        return _extract_json(text)

    async def complete_text(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int | None = None,
    ) -> str:
        """Send a message list to the model and return the raw text reply."""
        if not self.enabled:
            raise RuntimeError("AIService is disabled (no LLM provider configured).")

        if self._provider == "ollama":
            return await self._ollama_complete(system, messages, max_tokens)

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
        """Stream the model's reply as incremental text chunks."""
        if not self.enabled:
            raise RuntimeError("AIService is disabled (no LLM provider configured).")

        if self._provider == "ollama":
            async for chunk in self._ollama_stream(system, messages, max_tokens):
                yield chunk
            return

        async with self._client.messages.stream(
            model=settings.llm_model,
            max_tokens=max_tokens or settings.llm_max_tokens,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # --- Ollama backend (local, no API key) ---

    def _ollama_payload(
        self, system: str, messages: list[dict], max_tokens: int | None, stream: bool
    ) -> dict:
        return {
            "model": settings.ollama_model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": stream,
            "options": {"num_predict": max_tokens or settings.llm_max_tokens},
        }

    async def _ollama_complete(
        self, system: str, messages: list[dict], max_tokens: int | None
    ) -> str:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=self._ollama_payload(system, messages, max_tokens, stream=False),
            )
            resp.raise_for_status()
            return (resp.json().get("message") or {}).get("content", "").strip()

    async def _ollama_stream(
        self, system: str, messages: list[dict], max_tokens: int | None
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/chat",
                json=self._ollama_payload(system, messages, max_tokens, stream=True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    chunk = (data.get("message") or {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        return


def friendly_llm_error(exc: Exception) -> str | None:
    """Map a provider exception to a user-facing (Russian) message, or None."""
    # Ollama (httpx) errors first: connection refused / model not pulled.
    if isinstance(exc, httpx.ConnectError | httpx.ConnectTimeout):
        return (
            f"Ollama недоступен по адресу {settings.ollama_base_url}. "
            "Убедитесь, что Ollama запущен (`ollama serve`)."
        )
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 404:
            return (
                f"Модель «{settings.ollama_model}» не найдена в Ollama. "
                f"Скачайте её: `ollama pull {settings.ollama_model}`."
            )
        return f"Ollama вернул ошибку {exc.response.status_code}. Проверьте логи Ollama."

    if anthropic is None or not isinstance(exc, anthropic.APIError):
        return None

    if isinstance(exc, anthropic.APIStatusError) and "credit balance is too low" in str(exc):
        return (
            "На аккаунте Anthropic закончились кредиты API. "
            "Пополните баланс в console.anthropic.com (Plans & Billing) — "
            "или переключитесь на локальную модель (LLM_PROVIDER=ollama в .env)."
        )
    if isinstance(exc, anthropic.AuthenticationError):
        return "Ключ ANTHROPIC_API_KEY недействителен (неверный или отозван). Проверьте .env."
    if isinstance(exc, anthropic.PermissionDeniedError):
        return "Этому API-ключу запрещён доступ к модели. Проверьте настройки ключа в консоли Anthropic."
    if isinstance(exc, anthropic.RateLimitError):
        return "Превышен лимит запросов к Anthropic API. Подождите минуту и повторите."
    if isinstance(exc, anthropic.InternalServerError):
        return "Сервис Anthropic временно перегружен. Попробуйте ещё раз чуть позже."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Нет соединения с Anthropic API. Проверьте интернет/прокси."
    return None


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
