"""ORM models. Importing this package registers all tables on Base.metadata."""
from app.models.interview import Interview, InterviewAnswer, InterviewQuestion
from app.models.resume import Resume
from app.models.user import User
from app.models.vacancy import Vacancy

__all__ = [
    "User",
    "Resume",
    "Interview",
    "InterviewQuestion",
    "InterviewAnswer",
    "Vacancy",
]
