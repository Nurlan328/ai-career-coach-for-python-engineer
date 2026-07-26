"""Billing / subscription schemas."""
from datetime import datetime

from pydantic import BaseModel


class PlanOut(BaseModel):
    id: str
    label: str
    price_usd: float
    interviews_per_month: int | None  # None = unlimited


class UsageOut(BaseModel):
    plan: str  # plan actually in force right now
    purchased_plan: str  # what was bought (differs while past_due)
    interviews_used: int
    interviews_limit: int | None
    status: str | None = None  # Stripe subscription status
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    manageable: bool = False  # portal available (has a Stripe customer)
    stripe_enabled: bool = False


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    mock: bool
    plan: str | None = None
    checkout_url: str | None = None


class PortalResponse(BaseModel):
    portal_url: str
