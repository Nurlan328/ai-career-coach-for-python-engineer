async def test_register_login_me(client):
    r = await client.post(
        "/api/auth/register", json={"email": "a@b.com", "password": "secret123"}
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/auth/login", data={"username": "a@b.com", "password": "secret123"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


async def test_duplicate_register_conflicts(client):
    await client.post(
        "/api/auth/register", json={"email": "d@b.com", "password": "secret123"}
    )
    r = await client.post(
        "/api/auth/register", json={"email": "d@b.com", "password": "secret123"}
    )
    assert r.status_code == 409


async def test_login_wrong_password(client):
    await client.post(
        "/api/auth/register", json={"email": "e@b.com", "password": "secret123"}
    )
    r = await client.post(
        "/api/auth/login", data={"username": "e@b.com", "password": "nope"}
    )
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
