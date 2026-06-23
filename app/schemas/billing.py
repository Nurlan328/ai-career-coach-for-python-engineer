"""Billing / subscription schemas."""
from pydantic import BaseModel


class PlanOut(BaseModel):
    id: str
    label: str
    price_usd: float
    interviews_per_month: int | None  # None = unlimited


class UsageOut(BaseModel):
    plan: str
    interviews_used: int
    interviews_limit: int | None


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    mock: bool
    plan: str | None = None
    checkout_url: str | None = None
