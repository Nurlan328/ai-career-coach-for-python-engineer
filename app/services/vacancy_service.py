"""Vacancy analysis, resume↔vacancy gap analysis, and prep roadmap.

Like the other services: uses Claude when ANTHROPIC_API_KEY is set, otherwise a
deterministic heuristic so every endpoint works offline.
"""
import logging
import math

from app.schemas.vacancy import GapAnalysis, Roadmap, RoadmapWeek, VacancyAnalysis
from app.services.ai_service import ai
from app.services.resume_service import _SKILL_KEYWORDS

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a senior Python backend hiring expert. You analyze job postings and "
    "compare them against candidate resumes. Respond in the same language as the "
    "input (default: Russian)."
)


# ---------------------------------------------------------------- analyze vacancy
def _vacancy_prompt(description: str) -> str:
    return (
        "Analyze this job posting for a Python backend role.\n"
        "Return ONLY a JSON object with keys:\n"
        '  "required_skills" (array of technology/skill strings),\n'
        '  "summary" (string, 2-3 sentences on what the role wants).\n\n'
        f"Posting:\n{description[:8000]}"
    )


async def analyze_vacancy(description: str) -> VacancyAnalysis:
    if ai.enabled:
        try:
            data = await ai.complete_json(_SYSTEM, _vacancy_prompt(description))
            return VacancyAnalysis(
                required_skills=list(data.get("required_skills", [])),
                summary=str(data.get("summary", "")),
            )
        except Exception:  # noqa: BLE001
            logger.exception("LLM vacancy analysis failed; using heuristic")

    skills = _extract_skills(description)
    return VacancyAnalysis(
        required_skills=skills,
        summary=(
            f"Найдено требований: {len(skills)}. "
            "Эвристический разбор без LLM — задайте ANTHROPIC_API_KEY для детального анализа."
        ),
    )


def _extract_skills(text: str) -> list[str]:
    low = text.lower()
    return [s for s, keys in _SKILL_KEYWORDS.items() if any(k in low for k in keys)]


# ------------------------------------------------------------------ gap analysis
async def compare(
    resume_skills: list[str],
    vacancy_skills: list[str],
    vacancy_description: str,
) -> GapAnalysis:
    have = {s.lower() for s in resume_skills}
    matched = [s for s in vacancy_skills if s.lower() in have]
    missing = [s for s in vacancy_skills if s.lower() not in have]
    score = round(100 * len(matched) / max(1, len(vacancy_skills)), 1)

    if ai.enabled:
        try:
            prompt = (
                "Compare the candidate against the vacancy and suggest what to study.\n"
                f"Vacancy required skills: {vacancy_skills}\n"
                f"Candidate skills: {resume_skills}\n"
                f"Vacancy text (excerpt): {vacancy_description[:3000]}\n\n"
                "Return ONLY a JSON object with keys: "
                '"topics_to_study" (array of concrete topics to learn), '
                '"summary" (string, 2-3 sentences).'
            )
            data = await ai.complete_json(_SYSTEM, prompt)
            return GapAnalysis(
                match_score=score,
                matched_skills=matched,
                missing_skills=missing,
                topics_to_study=list(data.get("topics_to_study", missing)),
                summary=str(data.get("summary", "")),
            )
        except Exception:  # noqa: BLE001
            logger.exception("LLM gap analysis failed; using heuristic")

    return GapAnalysis(
        match_score=score,
        matched_skills=matched,
        missing_skills=missing,
        topics_to_study=missing,
        summary=(
            f"Совпадение по навыкам: {score}%. "
            + (f"Стоит подтянуть: {', '.join(missing)}." if missing else "Профиль закрывает требования.")
        ),
    )


# ---------------------------------------------------------------------- roadmap
async def generate_roadmap(
    topics: list[str], level: str, weeks: int
) -> Roadmap:
    if ai.enabled:
        try:
            prompt = (
                f"Build a {weeks}-week study roadmap for a {level} Python backend "
                f"engineer to master these topics: {topics}.\n"
                "Return ONLY a JSON object with keys: "
                '"summary" (string) and "weeks" (array of objects with '
                '"week" (int), "focus" (string), "topics" (string array), '
                '"resources" (string array)).'
            )
            data = await ai.complete_json(_SYSTEM, prompt)
            week_items = [
                RoadmapWeek(
                    week=int(w.get("week", i + 1)),
                    focus=str(w.get("focus", "")),
                    topics=list(w.get("topics", [])),
                    resources=list(w.get("resources", [])),
                )
                for i, w in enumerate(data.get("weeks", []))
            ]
            if week_items:
                return Roadmap(
                    level=level,
                    summary=str(data.get("summary", "")),
                    weeks=week_items,
                )
        except Exception:  # noqa: BLE001
            logger.exception("LLM roadmap failed; using heuristic")

    return _heuristic_roadmap(topics, level, weeks)


def _heuristic_roadmap(topics: list[str], level: str, weeks: int) -> Roadmap:
    topics = topics or ["Python Core", "FastAPI", "PostgreSQL"]
    per_week = max(1, math.ceil(len(topics) / weeks))
    plan: list[RoadmapWeek] = []
    for w in range(weeks):
        chunk = topics[w * per_week : (w + 1) * per_week]
        if not chunk:
            break
        plan.append(
            RoadmapWeek(
                week=w + 1,
                focus=", ".join(chunk),
                topics=chunk,
                resources=["Официальная документация", "Практика: мини-проект, тесты"],
            )
        )
    return Roadmap(
        level=level,
        summary="План сгенерирован эвристикой без LLM — задайте ANTHROPIC_API_KEY для детального плана.",
        weeks=plan,
    )
