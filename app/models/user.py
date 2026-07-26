"""User account model."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.interview import Interview
    from app.models.resume import Resume
    from app.models.vacancy import Vacancy


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Detected experience level: junior / middle / senior
    level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Plan the user has purchased. Actual entitlement also depends on
    # subscription_status — see billing.effective_plan().
    subscription_plan: Mapped[str] = mapped_column(String(50), default="free")

    # --- Stripe subscription state (mirrored from webhooks) ---
    # Stripe is the source of truth; these columns are a local cache so that
    # quota checks never need a network call.
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    # active / trialing / past_due / canceled / incomplete / unpaid
    subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false(), default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    vacancies: Mapped[list["Vacancy"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
