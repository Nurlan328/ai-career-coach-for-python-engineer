import asyncio

from tests.conftest import register_and_login

RESUME = b"Python backend developer: FastAPI, PostgreSQL, Redis, Docker, asyncio. Senior."


async def test_process_resume_task_updates_db(client):
    headers = await register_and_login(client)
    r = await client.post(
        "/api/resumes/upload",
        headers=headers,
        files={"file": ("cv.txt", RESUME, "text/plain")},
    )
    resume_id = r.json()["id"]

    # Run the Celery task locally in a worker thread (avoids a nested event loop).
    from app.worker.tasks import process_resume

    result = await asyncio.to_thread(lambda: process_resume.apply(args=[resume_id]).get())
    assert result["status"] == "done"
    assert result["level"] in {"junior", "middle", "senior"}

    r = await client.get(f"/api/resumes/{resume_id}/analysis", headers=headers)
    assert r.json()["detected_level"] in {"junior", "middle", "senior"}


async def test_reanalyze_endpoint_eager(client, headers):
    r = await client.post(
        "/api/resumes/upload",
        headers=headers,
        files={"file": ("cv.txt", RESUME, "text/plain")},
    )
    resume_id = r.json()["id"]

    r = await client.post(f"/api/resumes/{resume_id}/reanalyze", headers=headers)
    assert r.status_code == 202
    assert r.json()["status"] == "done"
