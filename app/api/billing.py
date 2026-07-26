"""Billing endpoints: plans, current usage, checkout, portal, Stripe webhook."""
import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanOut,
    PortalResponse,
    UsageOut,
)
from app.services import billing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
async def list_plans() -> list[dict]:
    return billing.plans()


@router.get("/me", response_model=UsageOut)
async def my_usage(current_user: CurrentUser, db: DbSession) -> dict:
    return await billing.usage(db, current_user)


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    payload: CheckoutRequest, current_user: CurrentUser, db: DbSession
) -> CheckoutResponse:
    try:
        result = await billing.create_checkout(db, current_user, payload.plan)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except billing.BillingConfigError as exc:
        # Our misconfiguration, not the caller's fault.
        logger.error("Billing misconfigured: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Оплата временно недоступна.",
        ) from exc
    except billing.BillingProviderError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Stripe недоступен, попробуйте позже.",
        ) from exc
    return CheckoutResponse(**result)


@router.post("/sync", response_model=UsageOut)
async def sync(current_user: CurrentUser, db: DbSession) -> dict:
    """Re-read subscription state from Stripe (used on the post-checkout return)."""
    try:
        await billing.sync_from_stripe(db, current_user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except billing.BillingProviderError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Stripe недоступен, попробуйте позже.",
        ) from exc
    return await billing.usage(db, current_user)


@router.post("/portal", response_model=PortalResponse)
async def portal(current_user: CurrentUser, db: DbSession) -> PortalResponse:
    """One-time link into the Stripe customer portal (cancel / change card)."""
    try:
        result = await billing.create_portal_session(db, current_user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except billing.BillingProviderError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Stripe недоступен, попробуйте позже.",
        ) from exc
    return PortalResponse(**result)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: DbSession) -> dict:
    """Public endpoint — authenticated solely by the Stripe signature header.

    Status codes matter here: 400 tells Stripe the delivery is broken and must
    not be retried, anything 5xx makes it retry with backoff. So a bad signature
    is a 400, while an internal failure must be allowed to bubble up as a 500.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        return await billing.handle_webhook(db, payload, signature)
    except billing.WebhookSignatureError as exc:
        logger.warning("Rejected Stripe webhook: %s", exc)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        ) from exc
