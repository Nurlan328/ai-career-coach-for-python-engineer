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
