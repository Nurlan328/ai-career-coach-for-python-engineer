"""Vacancy / gap-analysis / roadmap schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VacancyAnalyzeRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=20)


class VacancyAnalysis(BaseModel):
    required_skills: list[str] = []
    summary: str


class VacancyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None = None
    company: str | None = None
    required_skills: list[str] | None = None
    ai_summary: str | None = None
    created_at: datetime


class VacancyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None = None
    company: str | None = None
    created_at: datetime


class CompareRequest(BaseModel):
    vacancy_id: int
    resume_id: int


class GapAnalysis(BaseModel):
    match_score: float  # 0..100
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    topics_to_study: list[str] = []
    summary: str


class RoadmapRequest(BaseModel):
    vacancy_id: int
    resume_id: int
    weeks: int = Field(default=4, ge=1, le=12)


class RoadmapWeek(BaseModel):
    week: int
    focus: str
    topics: list[str] = []
    resources: list[str] = []


class Roadmap(BaseModel):
    level: str
    summary: str
    weeks: list[RoadmapWeek] = []
