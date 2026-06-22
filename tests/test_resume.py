RESUME = (
    b"Senior Python backend developer. FastAPI, PostgreSQL, Redis, Celery, Docker, "
    b"asyncio/await. REST API, microservices, pytest. Led a team."
)


async def test_upload_and_analyze(client, headers):
    r = await client.post(
        "/api/resumes/upload",
        headers=headers,
        files={"file": ("cv.txt", RESUME, "text/plain")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "FastAPI" in (body["skills"] or [])
    assert body["detected_level"] in {"junior", "middle", "senior"}

    r = await client.get(f"/api/resumes/{body['id']}/analysis", headers=headers)
    assert r.status_code == 200


async def test_unsupported_file_type(client, headers):
    r = await client.post(
        "/api/resumes/upload",
        headers=headers,
        files={"file": ("x.bin", b"\x00\x01\x02", "application/octet-stream")},
    )
    assert r.status_code == 415


async def test_resume_not_found(client, headers):
    r = await client.get("/api/resumes/9999/analysis", headers=headers)
    assert r.status_code == 404
