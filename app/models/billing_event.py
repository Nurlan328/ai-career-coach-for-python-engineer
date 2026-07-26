"""Ledger of consumed Stripe webhook events (delivery is at-least-once)."""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StripeEvent(Base):
    """One row per processed Stripe event id.

    Stripe retries a webhook until it gets a 2xx, and can deliver the same event
    more than once even after success. The primary key is the Stripe event id, so
    a duplicate delivery fails the INSERT and we skip re-applying its effects.
    """

    __tablename__ = "stripe_events"

    # e.g. "evt_1P9x2Y2eZvKYlo2C..."
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[str] = mapped_column(String(100))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
