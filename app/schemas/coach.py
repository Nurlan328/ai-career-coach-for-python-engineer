"""Schemas for the free-form Python tutor ('coach') endpoint."""
from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=4000,
        examples=["Чем asyncio.gather отличается от asyncio.create_task?"],
    )
    # Optional topic hint to focus the answer.
    category: str | None = Field(default=None, examples=["Async Python"])
    # Prior turns for multi-turn / follow-up questions (oldest first).
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class AskResponse(BaseModel):
    question: str
    answer: str
    # "ai" — answered by Claude; "unavailable" — no API key; "error" — LLM call failed.
    source: str
    model: str | None = None


class RagSource(BaseModel):
    title: str
    source: str
    snippet: str
    score: float


class RagResponse(BaseModel):
    question: str
    answer: str
    source: str  # "ai" (grounded by Claude) or "offline" (snippets only)
    sources: list[RagSource] = []
