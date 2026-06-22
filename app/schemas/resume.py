"""Resume request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeAnalysis(BaseModel):
    """Structured output of the resume analysis step."""

    summary: str
    detected_level: str
    skills: list[str] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    ai_summary: str | None = None
    detected_level: str | None = None
    skills: list[str] | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    recommendations: list[str] | None = None
    created_at: datetime


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    detected_level: str | None = None
    created_at: datetime
