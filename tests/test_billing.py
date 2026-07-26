START = {"category": "FastAPI", "level": "middle", "num_questions": 1}


async def test_plans_listed(client, headers):
    r = await client.get("/api/billing/plans", headers=headers)
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert {"free", "pro"} <= ids


async def test_default_plan_and_usage(client, headers):
    r = await client.get("/api/billing/me", headers=headers)
    body = r.json()
    assert body["plan"] == "free"
    assert body["interviews_used"] == 0
    assert body["interviews_limit"] == 3  # default free limit


async def test_free_quota_is_enforced(client, headers):
    # Free plan allows 3 interviews/month; the 4th is blocked with 402.
    for _ in range(3):
        r = await client.post("/api/interviews/start", headers=headers, json=START)
        assert r.status_code == 201, r.text
    r = await client.post("/api/interviews/start", headers=headers, json=START)
    assert r.status_code == 402, r.text


async def test_mock_checkout_upgrades_and_lifts_limit(client, headers):
    # No Stripe key in tests -> mock checkout upgrades instantly.
    r = await client.post("/api/billing/checkout", headers=headers, json={"plan": "pro"})
    assert r.status_code == 200 and r.json()["mock"] is True

    r = await client.get("/api/billing/me", headers=headers)
    assert r.json()["plan"] == "pro"
    assert r.json()["interviews_limit"] is None  # unlimited

    # Pro can exceed the old free limit.
    for _ in range(5):
        r = await client.post("/api/interviews/start", headers=headers, json=START)
        assert r.status_code == 201, r.text


async def test_checkout_rejects_free_plan(client, headers):
    r = await client.post("/api/billing/checkout", headers=headers, json={"plan": "free"})
    assert r.status_code == 400


async def test_portal_without_stripe_is_rejected(client, headers):
    r = await client.post("/api/billing/portal", headers=headers)
    assert r.status_code == 400


async def test_webhook_ignored_when_billing_unconfigured(client):
    r = await client.post("/api/billing/webhook", content=b"{}")
    assert r.status_code == 200 and r.json()["status"] == "ignored"


WEBHOOK_SECRET = "whsec_test_secret"


def _enable_stripe(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_dummy")
    monkeypatch.setattr(settings, "stripe_webhook_secret", WEBHOOK_SECRET)
    monkeypatch.setattr(settings, "stripe_price_pro", "price_dummy")


async def _post_event(client, event: dict):
    """Send a genuinely signed webhook, exactly as Stripe would.

    Signing for real (instead of stubbing construct_event) is deliberate: a stub
    hands the handlers plain dicts, which hid the fact that the SDK's own parser
    returns StripeObjects with no .get().
    """
    import hashlib
    import hmac
    import json
    import time

    body = json.dumps(event).encode()
    ts = int(time.time())
    mac = hmac.new(
        WEBHOOK_SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return await client.post(
        "/api/billing/webhook",
        content=body,
        headers={"stripe-signature": f"t={ts},v1={mac}"},
    )


async def test_webhook_rejects_bad_signature(client, monkeypatch):
    _enable_stripe(monkeypatch)
    r = await client.post(
        "/api/billing/webhook",
        content=b'{"id":"evt_1","type":"customer.subscription.updated"}',
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert r.status_code == 400


def _subscription_event(event_id: str, status: str) -> dict:
    return {
        "id": event_id,
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test",
                "object": "subscription",
                "customer": "cus_test",
                "status": status,
                "cancel_at_period_end": False,
                # Newer API versions put this on the item, not the subscription.
                "items": {
                    "object": "list",
                    "data": [
                        {
                            "price": {"id": "price_dummy"},
                            "current_period_end": 1893456000,  # 2030-01-01
                        }
                    ],
                },
                "metadata": {"plan": "pro"},
            }
        },
    }


async def _attach_customer(customer_id: str = "cus_test") -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User))
        user.stripe_customer_id = customer_id
        await db.commit()


async def test_webhook_activates_subscription_and_is_idempotent(
    client, headers, monkeypatch
):
    _enable_stripe(monkeypatch)
    await _attach_customer()

    event = _subscription_event("evt_active", "active")
    r = await _post_event(client, event)
    assert r.status_code == 200 and r.json()["status"] == "ok", r.text

    body = (await client.get("/api/billing/me", headers=headers)).json()
    assert body["plan"] == "pro"
    assert body["status"] == "active"
    assert body["interviews_limit"] is None
    assert body["current_period_end"].startswith("2030-01-01")

    # Stripe re-delivers the same event: it must be a no-op, not a second upgrade.
    r = await _post_event(client, event)
    assert r.json()["status"] == "duplicate"


async def test_past_due_subscription_falls_back_to_free_limits(
    client, headers, monkeypatch
):
    _enable_stripe(monkeypatch)
    await _attach_customer()

    await _post_event(client, _subscription_event("evt_a", "active"))
    await _post_event(client, _subscription_event("evt_b", "past_due"))

    body = (await client.get("/api/billing/me", headers=headers)).json()
    assert body["plan"] == "free"  # entitlement dropped
    assert body["purchased_plan"] == "pro"  # but we remember what was bought
    assert body["interviews_limit"] == 3

    for _ in range(3):
        assert (
            await client.post("/api/interviews/start", headers=headers, json=START)
        ).status_code == 201
    r = await client.post("/api/interviews/start", headers=headers, json=START)
    assert r.status_code == 402


async def test_subscription_deleted_downgrades(client, headers, monkeypatch):
    _enable_stripe(monkeypatch)
    await _attach_customer()

    await _post_event(client, _subscription_event("evt_c", "active"))

    deleted = _subscription_event("evt_d", "canceled")
    deleted["type"] = "customer.subscription.deleted"
    await _post_event(client, deleted)

    body = (await client.get("/api/billing/me", headers=headers)).json()
    assert body["plan"] == "free" and body["purchased_plan"] == "free"
    assert body["current_period_end"] is None


async def test_webhook_rejects_stale_timestamp(client, monkeypatch):
    """A correctly signed but old request must not replay."""
    import hashlib
    import hmac
    import json
    import time

    _enable_stripe(monkeypatch)
    body = json.dumps(_subscription_event("evt_replay", "active")).encode()
    ts = int(time.time()) - 3600  # an hour past the 300s tolerance
    mac = hmac.new(
        WEBHOOK_SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256
    ).hexdigest()
    r = await client.post(
        "/api/billing/webhook",
        content=body,
        headers={"stripe-signature": f"t={ts},v1={mac}"},
    )
    assert r.status_code == 400


async def test_webhook_rejects_malformed_body(client, monkeypatch):
    import hashlib
    import hmac
    import time

    _enable_stripe(monkeypatch)
    body = b"not json at all"
    ts = int(time.time())
    mac = hmac.new(
        WEBHOOK_SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256
    ).hexdigest()
    r = await client.post(
        "/api/billing/webhook",
        content=body,
        headers={"stripe-signature": f"t={ts},v1={mac}"},
    )
    assert r.status_code == 400
