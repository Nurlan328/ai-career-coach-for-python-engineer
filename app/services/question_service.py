"""Generate interview questions, via Claude when available, else the static bank."""
import logging

from app.schemas.question import GeneratedQuestion
from app.services.ai_service import ai
from app.services.question_bank import get_bank_questions

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a senior Python backend interviewer. You create precise, practical "
    "interview questions for backend engineers. Always answer in the same language "
    "as the requested category context (default: Russian)."
)


def _prompt(category: str, level: str, count: int) -> str:
    return (
        f"Generate {count} interview questions for the category '{category}' "
        f"targeting a {level}-level Python backend engineer.\n"
        "For each question include a concise model/expected answer (2-4 sentences).\n"
        'Return ONLY a JSON array of objects with keys: '
        '"question_text", "difficulty", "expected_answer". '
        f'Use "{level}" as the difficulty value.'
    )


async def generate_questions(
    category: str, level: str = "middle", count: int = 5
) -> tuple[list[GeneratedQuestion], str]:
    """Return (questions, source) where source is 'ai' or 'bank'."""
    if ai.enabled:
        try:
            data = await ai.complete_json(_SYSTEM, _prompt(category, level, count))
            items = data if isinstance(data, list) else data.get("questions", [])
            questions = [
                GeneratedQuestion(
                    question_text=item["question_text"],
                    category=category,
                    difficulty=str(item.get("difficulty", level)),
                    expected_answer=item.get("expected_answer"),
                )
                for item in items
                if item.get("question_text")
            ]
            if questions:
                return questions[:count], "ai"
        except Exception:  # noqa: BLE001 - never fail the request on LLM error
            logger.exception("LLM question generation failed; using question bank")

    questions = [
        GeneratedQuestion(
            question_text=text,
            category=category,
            difficulty=level,
            expected_answer=None,
        )
        for text in get_bank_questions(category, count)
    ]
    return questions, "bank"
