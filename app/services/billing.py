"""Subscription plans, usage limits and Stripe billing.

Two modes, chosen by whether STRIPE_SECRET_KEY is set:

* **mock** — no key: checkout upgrades the user instantly, no charge. Keeps the
  whole flow demoable offline (and is what the test-suite exercises).
* **real** — Stripe Checkout (hosted page) + the customer portal for
  cancel/update-card, with subscription state mirrored back through webhooks.

Stripe is the source of truth for subscription state; the columns on ``users``
are a local cache so quota checks never make a network call.
"""
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.billing_event import StripeEvent
from app.models.interview import Interview
from app.models.user import User

logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:  # pragma: no cover
    stripe = None

# Statuses that actually entitle the user to the paid plan. "past_due" is
# deliberately excluded: the card failed, so we fall back to free limits while
# Stripe retries (it may still recover, hence we keep the subscription id).
ACTIVE_STATUSES = {"active", "trialing"}


class BillingConfigError(RuntimeError):
    """Stripe is enabled but misconfigured (missing price id, etc.)."""


class BillingProviderError(RuntimeError):
    """Stripe itself failed (network, rate limit, invalid price id...)."""


class WebhookSignatureError(RuntimeError):
    """The webhook payload failed signature verification."""


# --------------------------------------------------------------------------- #
# Plans
# --------------------------------------------------------------------------- #
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


def effective_plan(user: User) -> dict:
    """The plan the user is entitled to *right now*.

    ``user.subscription_plan`` records what was bought; a Stripe-backed
    subscription only counts while its status is active/trialing. Mock upgrades
    have no subscription id and are always honoured.
    """
    if user.stripe_subscription_id and user.subscription_status not in ACTIVE_STATUSES:
        return plan_for("free")
    return plan_for(user.subscription_plan)


# --------------------------------------------------------------------------- #
# Usage / quota
# --------------------------------------------------------------------------- #
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
    plan = effective_plan(user)
    return {
        "plan": plan["id"],
        "purchased_plan": user.subscription_plan,
        "interviews_used": await interviews_this_month(db, user.id),
        "interviews_limit": plan["interviews_per_month"],
        "status": user.subscription_status,
        "current_period_end": user.subscription_current_period_end,
        "cancel_at_period_end": user.subscription_cancel_at_period_end,
        "manageable": bool(user.stripe_customer_id) and stripe_enabled(),
        "stripe_enabled": stripe_enabled(),
    }


async def check_interview_quota(db: AsyncSession, user: User) -> None:
    """Raise 402 if the user is at their monthly interview limit."""
    plan = effective_plan(user)
    limit = plan["interviews_per_month"]
    if limit is None:
        return
    used = await interviews_this_month(db, user.id)
    if used >= limit:
        detail = (
            f"Достигнут лимит интервью для тарифа {plan['label']} "
            f"({limit}/мес). Оформите Pro для безлимита."
        )
        if user.subscription_status == "past_due":
            detail = (
                "Не прошёл платёж по подписке Pro — доступ временно ограничен "
                "тарифом Free. Обновите карту в разделе управления подпиской."
            )
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


# --------------------------------------------------------------------------- #
# Stripe client
# --------------------------------------------------------------------------- #
def stripe_enabled() -> bool:
    return bool(settings.stripe_secret_key and stripe is not None)


@lru_cache(maxsize=1)
def _client():
    """Cached StripeClient. Async methods keep the event loop unblocked."""
    kwargs = {}
    if settings.stripe_api_version:
        kwargs["stripe_version"] = settings.stripe_api_version
    return stripe.StripeClient(settings.stripe_secret_key, **kwargs)


@asynccontextmanager
async def _stripe_errors(action: str):
    """Turn any SDK failure into one domain error the API layer can map."""
    try:
        yield
    except stripe.StripeError as exc:  # network, rate limit, bad price id...
        logger.exception("Stripe call failed (%s)", action)
        raise BillingProviderError(str(exc)) from exc


def _require_config() -> None:
    if not settings.stripe_price_pro:
        raise BillingConfigError(
            "STRIPE_PRICE_PRO не задан — нужен id recurring-цены из Stripe."
        )


async def ensure_customer(db: AsyncSession, user: User) -> str:
    """Return the user's Stripe customer id, creating it on first use.

    One customer per user, reused forever: that is what makes the portal, the
    invoice history and webhook lookups line up.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    async with _stripe_errors("create customer"):
        customer = await _client().v1.customers.create_async(
            params={
                "email": user.email,
                "name": user.full_name or None,
                "metadata": {"user_id": str(user.id)},
            },
            # Same key for the same user => a retry can't create a second customer.
            options={"idempotency_key": f"customer:{user.id}"},
        )
    user.stripe_customer_id = customer["id"]
    db.add(user)
    await db.commit()
    logger.info("Stripe: created customer %s for user %s", customer["id"], user.id)
    return customer["id"]


# --------------------------------------------------------------------------- #
# Checkout / portal
# --------------------------------------------------------------------------- #
async def create_checkout(db: AsyncSession, user: User, plan_name: str) -> dict:
    if plan_name not in {p["id"] for p in plans()} or plan_name == "free":
        raise ValueError("Unknown or non-purchasable plan")

    if not stripe_enabled():
        # Mock mode: upgrade immediately so the flow works without Stripe.
        user.subscription_plan = plan_name
        user.subscription_status = None
        db.add(user)
        await db.commit()
        logger.info("Mock checkout: user %s upgraded to %s", user.id, plan_name)
        return {"mock": True, "plan": plan_name}

    if user.stripe_subscription_id and user.subscription_status in ACTIVE_STATUSES:
        raise ValueError(
            "Подписка уже активна — управляйте ей через портал Stripe."
        )

    _require_config()
    customer_id = await ensure_customer(db, user)

    # Idempotency key bucketed by 5 minutes: a double-click or a retry reuses the
    # same Checkout Session instead of opening a second one, but a genuine new
    # attempt later still gets a fresh session.
    bucket = int(datetime.now(timezone.utc).timestamp()) // 300
    metadata = {"user_id": str(user.id), "plan": plan_name}

    async with _stripe_errors("create checkout session"):
        session = await _client().v1.checkout.sessions.create_async(
            params={
                "mode": "subscription",
                "customer": customer_id,
                "line_items": [{"price": settings.stripe_price_pro, "quantity": 1}],
                "success_url": settings.billing_success_url,
                "cancel_url": settings.billing_cancel_url,
                "client_reference_id": str(user.id),
                "metadata": metadata,
                # Copied onto the subscription itself, so subscription.* webhooks
                # carry the plan without a second lookup.
                "subscription_data": {"metadata": metadata},
                "allow_promotion_codes": True,
            },
            options={"idempotency_key": f"checkout:{user.id}:{plan_name}:{bucket}"},
        )
    logger.info("Stripe: checkout session %s for user %s", session["id"], user.id)
    return {"mock": False, "plan": plan_name, "checkout_url": session["url"]}


async def create_portal_session(db: AsyncSession, user: User) -> dict:
    """Stripe-hosted portal: cancel, resume, change card, download invoices.

    Building those screens ourselves would mean handling PCI-scope card input;
    the portal is the sanctioned way to let users manage a subscription.
    """
    if not stripe_enabled():
        raise ValueError("Stripe не настроен — портал управления недоступен.")
    if not user.stripe_customer_id:
        raise ValueError("У пользователя ещё нет подписки Stripe.")

    async with _stripe_errors("create portal session"):
        session = await _client().v1.billing_portal.sessions.create_async(
            params={
                "customer": user.stripe_customer_id,
                "return_url": settings.billing_portal_return_url,
            }
        )
    return {"portal_url": session["url"]}


# --------------------------------------------------------------------------- #
# Webhooks
# --------------------------------------------------------------------------- #
def _field(obj, key: str, default=None):
    """Read a field from a webhook dict *or* a StripeObject.

    Objects parsed from a webhook body are plain dicts, but anything fetched
    through the SDK comes back as a StripeObject — which, since stripe-python
    13, is not a dict subclass and has no ``.get()``. One accessor keeps the
    handlers working with both.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _items(subscription) -> list:
    return _field(_field(subscription, "items"), "data") or []


def _period_end(subscription) -> datetime | None:
    """current_period_end moved onto subscription items in newer API versions."""
    ts = _field(subscription, "current_period_end")
    if ts is None:
        items = _items(subscription)
        ts = _field(items[0], "current_period_end") if items else None
    return datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None


def _plan_from_subscription(subscription) -> str:
    """Which local plan this subscription grants (metadata first, then price)."""
    from_meta = _field(_field(subscription, "metadata"), "plan")
    if from_meta in {p["id"] for p in plans()}:
        return from_meta
    items = _items(subscription)
    price_id = _field(_field(items[0], "price"), "id") if items else None
    if price_id and price_id == settings.stripe_price_pro:
        return "pro"
    # Single paid plan today; log loudly if that ever stops being true.
    logger.warning("Unmapped Stripe price %s — defaulting to 'pro'", price_id)
    return "pro"


async def _user_for(db: AsyncSession, customer_id: str | None, user_id: str | None):
    if user_id:
        user = await db.get(User, int(user_id))
        if user:
            return user
    if customer_id:
        return await db.scalar(
            select(User).where(User.stripe_customer_id == customer_id)
        )
    return None


def _apply_subscription(user: User, subscription) -> None:
    user.stripe_subscription_id = _field(subscription, "id")
    user.subscription_status = _field(subscription, "status")
    user.subscription_cancel_at_period_end = bool(
        _field(subscription, "cancel_at_period_end")
    )
    user.subscription_current_period_end = _period_end(subscription)
    user.subscription_plan = _plan_from_subscription(subscription)


def _downgrade(user: User, status_: str = "canceled") -> None:
    user.subscription_plan = "free"
    user.subscription_status = status_
    user.stripe_subscription_id = None
    user.subscription_cancel_at_period_end = False
    user.subscription_current_period_end = None


async def _claim_event(db: AsyncSession, event) -> bool:
    """Insert the event id; False if it was already processed.

    Claim-before-work (rather than check-then-act) so two concurrent deliveries
    of the same event can't both pass the check — the PK conflict decides.
    """
    db.add(StripeEvent(id=event["id"], type=event["type"]))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return False
    return True


async def handle_webhook(db: AsyncSession, payload: bytes, signature: str) -> dict:
    """Verify, de-duplicate and apply a Stripe event.

    The signature check is the *only* authentication this endpoint has — it is
    public, so anyone can POST to it. Without a configured webhook secret we
    refuse to trust the payload rather than processing it unverified.
    """
    if not stripe_enabled() or not settings.stripe_webhook_secret:
        logger.warning("Stripe webhook received but billing is not configured")
        return {"status": "ignored"}

    # Verify the HMAC, then parse the body ourselves. construct_event() would
    # hand back a StripeObject tree instead of plain dicts, and those have no
    # .get() — decoding the JSON keeps every handler below working on dicts.
    try:
        # verify_header wants str, not bytes ("%d.%s" of bytes signs its repr),
        # and unlike construct_event it skips the timestamp check unless a
        # tolerance is passed — without it, a captured request replays forever.
        body = payload.decode("utf-8")
        stripe.WebhookSignature.verify_header(
            body,
            signature,
            settings.stripe_webhook_secret,
            tolerance=stripe.Webhook.DEFAULT_TOLERANCE,
        )
        event = json.loads(body)
    except stripe.SignatureVerificationError as exc:
        raise WebhookSignatureError(str(exc)) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise WebhookSignatureError(f"malformed payload: {exc}") from exc

    if not await _claim_event(db, event):
        logger.info("Stripe: duplicate event %s ignored", event["id"])
        return {"status": "duplicate"}

    obj = event["data"]["object"]
    event_type = event["type"]
    handled = True

    if event_type == "checkout.session.completed":
        user = await _user_for(
            db, obj.get("customer"), obj.get("client_reference_id")
        )
        if user is None:
            logger.error("Stripe: no user for checkout session %s", obj.get("id"))
        else:
            if not user.stripe_customer_id and obj.get("customer"):
                user.stripe_customer_id = obj["customer"]
            sub_id = obj.get("subscription")
            if sub_id:
                # The session payload carries no subscription details; fetch it.
                subscription = await _client().v1.subscriptions.retrieve_async(sub_id)
                _apply_subscription(user, subscription)
                logger.info(
                    "Stripe: user %s subscribed to %s (%s)",
                    user.id,
                    user.subscription_plan,
                    user.subscription_status,
                )

    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
    }:
        user = await _user_for(
            db, obj.get("customer"), (obj.get("metadata") or {}).get("user_id")
        )
        if user is not None:
            _apply_subscription(user, obj)

    elif event_type == "customer.subscription.deleted":
        user = await _user_for(
            db, obj.get("customer"), (obj.get("metadata") or {}).get("user_id")
        )
        if user is not None:
            _downgrade(user)
            logger.info("Stripe: user %s downgraded to free", user.id)

    elif event_type == "invoice.payment_failed":
        user = await _user_for(db, obj.get("customer"), None)
        if user is not None and user.stripe_subscription_id:
            # subscription.updated normally follows with the authoritative
            # status; this is a fast-path so entitlement drops immediately.
            user.subscription_status = "past_due"
            logger.warning("Stripe: payment failed for user %s", user.id)

    else:
        handled = False
        logger.debug("Stripe: unhandled event type %s", event_type)

    await db.commit()
    return {"status": "ok" if handled else "unhandled", "type": event_type}
