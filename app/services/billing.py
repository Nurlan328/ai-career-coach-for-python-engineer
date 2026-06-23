"""Subscription plans, usage limits and Stripe checkout.

Mirrors the other services' optionality: without STRIPE_SECRET_KEY, checkout runs
in mock mode (instant upgrade, no charge) so the whole flow is demoable offline.
"""
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.interview import Interview
from app.models.user import User

logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:  # pragma: no cover
    stripe = None


def plans() -> list[dict]:
    """Available plans. interviews_per_month=None means unlimited."""
    return [
        {
            "id": "free",
            "label": "Free",
            "price_usd": 0.0,
            "interviews_per_month": settings.free_interviews_per_month,
        },
        {
            "id": "pro",
            "label": "Pro",
            "price_usd": settings.pro_price_usd,
            "interviews_per_month": None,
        },
    ]


def plan_for(name: str | None) -> dict:
    by_id = {p["id"]: p for p in plans()}
    return by_id.get(name or "free", by_id["free"])


def stripe_enabled() -> bool:
    return bool(settings.stripe_secret_key and stripe is not None)


async def interviews_this_month(db: AsyncSession, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = await db.scalar(
        select(func.count(Interview.id)).where(
            Interview.user_id == user_id, Interview.created_at >= start
        )
    )
    return int(count or 0)


async def usage(db: AsyncSession, user: User) -> dict:
    plan = plan_for(user.subscription_plan)
    return {
        "plan": user.subscription_plan,
        "interviews_used": await interviews_this_month(db, user.id),
        "interviews_limit": plan["interviews_per_month"],
    }


async def check_interview_quota(db: AsyncSession, user: User) -> None:
    """Raise 402 if the user is at their monthly interview limit."""
    plan = plan_for(user.subscription_plan)
    limit = plan["interviews_per_month"]
    if limit is None:
        return
    used = await interviews_this_month(db, user.id)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Достигнут лимит интервью для тарифа {plan['label']} "
                f"({limit}/мес). Оформите Pro для безлимита."
            ),
        )


async def create_checkout(db: AsyncSession, user: User, plan_name: str) -> dict:
    if plan_name not in {p["id"] for p in plans()} or plan_name == "free":
        raise ValueError("Unknown or non-purchasable plan")

    if not stripe_enabled():
        # Mock mode: upgrade immediately so the flow works without Stripe.
        user.subscription_plan = plan_name
        db.add(user)
        await db.commit()
        logger.info("Mock checkout: user %s upgraded to %s", user.id, plan_name)
        return {"mock": True, "plan": plan_name}

    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": settings.stripe_price_pro, "quantity": 1}],
        success_url=settings.billing_success_url,
        cancel_url=settings.billing_cancel_url,
        client_reference_id=str(user.id),
        metadata={"plan": plan_name},
    )
    return {"mock": False, "checkout_url": session.url}


async def handle_webhook(db: AsyncSession, payload: bytes, signature: str) -> dict:
    if not stripe_enabled() or not settings.stripe_webhook_secret:
        return {"status": "ignored"}

    stripe.api_key = settings.stripe_secret_key
    event = stripe.Webhook.construct_event(
        payload, signature, settings.stripe_webhook_secret
    )
    if event["type"] == "checkout.session.completed":
        obj = event["data"]["object"]
        user_id = obj.get("client_reference_id")
        plan_name = (obj.get("metadata") or {}).get("plan", "pro")
        if user_id:
            user = await db.get(User, int(user_id))
            if user:
                user.subscription_plan = plan_name
                await db.commit()
                logger.info("Stripe: user %s subscribed to %s", user_id, plan_name)
    return {"status": "ok"}
