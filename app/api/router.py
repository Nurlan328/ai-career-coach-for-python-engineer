"""Aggregate all API routers under a single APIRouter."""
from fastapi import APIRouter

from app.api import auth, coach, interviews, questions, resumes, vacancies

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
api_router.include_router(questions.router)
api_router.include_router(interviews.router)
api_router.include_router(vacancies.router)
api_router.include_router(coach.router)
