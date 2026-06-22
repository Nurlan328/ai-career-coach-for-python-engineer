async def test_ask_offline_is_unavailable(client, headers):
    r = await client.post(
        "/api/coach/ask", headers=headers, json={"question": "Что такое GIL?"}
    )
    assert r.status_code == 200
    assert r.json()["source"] == "unavailable"


async def test_ask_stream_offline(client, headers):
    async with client.stream(
        "POST",
        "/api/coach/ask/stream",
        headers=headers,
        json={"question": "Что такое event loop?"},
    ) as resp:
        assert resp.status_code == 200
        body = (await resp.aread()).decode("utf-8")
    assert "ANTHROPIC_API_KEY" in body


async def test_ask_requires_auth(client):
    r = await client.post("/api/coach/ask", json={"question": "hi there"})
    assert r.status_code == 401
