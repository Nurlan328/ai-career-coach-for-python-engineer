"""Billing endpoints: plans, current usage, checkout, Stripe webhook."""
from fastapi import APIRouter, HTTPException, Request, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanOut,
    UsageOut,
)
from app.services import billing

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
    return CheckoutResponse(**result)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: DbSession) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        return await billing.handle_webhook(db, payload, signature)
    except Exception as exc:  # noqa: BLE001 - invalid signature / payload
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid webhook"
        ) from exc
