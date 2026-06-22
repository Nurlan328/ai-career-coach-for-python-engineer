"""Analyze resume text, via Claude when available, else keyword heuristics."""
import logging

from app.schemas.resume import ResumeAnalysis
from app.services.ai_service import ai

logger = logging.getLogger(__name__)

# Skills the analyzer looks for (from the project spec).
_SKILL_KEYWORDS: dict[str, list[str]] = {
    "Python": ["python"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "SQLAlchemy": ["sqlalchemy"],
    "Django ORM": ["django orm"],
    "PostgreSQL": ["postgres", "postgresql", "psql"],
    "Redis": ["redis"],
    "Celery": ["celery"],
    "Docker": ["docker", "docker-compose", "dockerfile"],
    "async/await": ["async", "await", "asyncio"],
    "REST API": ["rest", "restful", "api"],
    "microservices": ["microservice", "микросерв"],
    "testing": ["pytest", "unittest", "test"],
    "Kubernetes": ["kubernetes", "k8s"],
    "RabbitMQ": ["rabbitmq", "amqp"],
    "gRPC": ["grpc"],
}

_SENIOR_HINTS = ["lead", "senior", "архитект", "architved", "architect", "mentor", "наставник"]
_JUNIOR_HINTS = ["junior", "intern", "стажёр", "стажер", "студент"]

_SYSTEM = (
    "You are a senior Python backend hiring expert. You analyze resumes and assess "
    "the candidate's level. Respond in the same language as the resume "
    "(default: Russian)."
)


def _prompt(text: str) -> str:
    return (
        "Analyze the following resume of a (Python) backend engineer.\n"
        "Return ONLY a JSON object with keys:\n"
        '  "summary" (string, 2-4 sentences),\n'
        '  "detected_level" (one of "junior", "middle", "senior"),\n'
        '  "skills" (string array of detected technologies),\n'
        '  "strengths" (string array),\n'
        '  "weaknesses" (string array),\n'
        '  "recommendations" (string array of how to improve the resume).\n\n'
        f"Resume:\n{text[:8000]}"
    )


async def analyze_resume(text: str) -> ResumeAnalysis:
    if ai.enabled:
        try:
            data = await ai.complete_json(_SYSTEM, _prompt(text))
            return ResumeAnalysis(
                summary=str(data.get("summary", "")),
                detected_level=str(data.get("detected_level", "middle")).lower(),
                skills=list(data.get("skills", [])),
                strengths=list(data.get("strengths", [])),
                weaknesses=list(data.get("weaknesses", [])),
                recommendations=list(data.get("recommendations", [])),
            )
        except Exception:  # noqa: BLE001
            logger.exception("LLM resume analysis failed; using heuristic fallback")

    return _heuristic_analysis(text)


def _heuristic_analysis(text: str) -> ResumeAnalysis:
    low = text.lower()
    skills = [
        skill
        for skill, keys in _SKILL_KEYWORDS.items()
        if any(k in low for k in keys)
    ]
    level = _detect_level(low, skills)

    return ResumeAnalysis(
        summary=(
            f"Найдено навыков: {len(skills)}. Предполагаемый уровень: {level}. "
            "Эвристический анализ без LLM — задайте ANTHROPIC_API_KEY для детального разбора."
        ),
        detected_level=level,
        skills=skills,
        strengths=[f"Владеет: {s}" for s in skills[:5]],
        weaknesses=["Анализ выполнен эвристикой, без LLM."],
        recommendations=[
            "Добавьте измеримые результаты (метрики, нагрузку, размер команды).",
            "Укажите версии и контекст использования технологий.",
        ],
    )


def _detect_level(low: str, skills: list[str]) -> str:
    if any(h in low for h in _SENIOR_HINTS) or len(skills) >= 9:
        return "senior"
    if any(h in low for h in _JUNIOR_HINTS) or len(skills) <= 3:
        return "junior"
    return "middle"
