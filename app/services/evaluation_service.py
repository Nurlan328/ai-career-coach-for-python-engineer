"""Evaluate a candidate's answer, via Claude when available, else a heuristic."""
import logging

from app.schemas.interview import AnswerFeedback
from app.services.ai_service import ai

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a Senior Python Backend Interviewer. You evaluate candidate answers "
    "fairly and concretely. Respond in the same language as the question "
    "(default: Russian)."
)


def _prompt(category: str, question: str, answer: str) -> str:
    return (
        "Evaluate the candidate answer by these criteria:\n"
        "1. Technical accuracy\n2. Depth of understanding\n"
        "3. Production experience\n4. Code/API design thinking\n"
        "5. Senior-level reasoning\n\n"
        f"Interview category: {category}\n"
        f"Question: {question}\n"
        f"Candidate answer: {answer}\n\n"
        "Return ONLY a JSON object with keys: "
        '"score" (integer 1-10), "strengths" (string array), '
        '"weaknesses" (string array), "missing_topics" (string array), '
        '"ideal_answer" (string).'
    )


async def evaluate_answer(category: str, question: str, answer: str) -> AnswerFeedback:
    if ai.enabled:
        try:
            data = await ai.complete_json(_SYSTEM, _prompt(category, question, answer))
            return AnswerFeedback(
                score=float(data.get("score", 0)),
                strengths=list(data.get("strengths", [])),
                weaknesses=list(data.get("weaknesses", [])),
                missing_topics=list(data.get("missing_topics", [])),
                ideal_answer=str(data.get("ideal_answer", "")),
            )
        except Exception:  # noqa: BLE001
            logger.exception("LLM evaluation failed; using heuristic fallback")

    return _heuristic_feedback(answer)


def _heuristic_feedback(answer: str) -> AnswerFeedback:
    """Very rough offline scoring based on answer length and specificity."""
    words = answer.split()
    n = len(words)
    if n < 15:
        score = 3.0
    elif n < 40:
        score = 5.0
    elif n < 90:
        score = 7.0
    else:
        score = 8.0

    return AnswerFeedback(
        score=score,
        strengths=["Ответ дан"] if n else [],
        weaknesses=[
            "Оценка выполнена эвристикой без LLM. "
            "Задайте ANTHROPIC_API_KEY для содержательной обратной связи."
        ],
        missing_topics=[],
        ideal_answer="",
    )
