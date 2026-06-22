"""Throwaway end-to-end smoke test (offline / no API key). Run: python smoke_test.py"""
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./_smoke.db"
os.environ["ANTHROPIC_API_KEY"] = ""

import httpx

from app.core.database import init_db
from app.main import app


async def main() -> None:
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # health
        r = await c.get("/")
        assert r.status_code == 200, r.text
        assert r.json()["llm_enabled"] is False

        # register
        r = await c.post("/api/auth/register", json={
            "email": "dev@example.com", "password": "secret123", "full_name": "Dev"})
        assert r.status_code == 201, r.text

        # duplicate -> 409
        r = await c.post("/api/auth/register", json={
            "email": "dev@example.com", "password": "secret123"})
        assert r.status_code == 409, r.text

        # login
        r = await c.post("/api/auth/login", data={
            "username": "dev@example.com", "password": "secret123"})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # me
        r = await c.get("/api/auth/me", headers=h)
        assert r.status_code == 200 and r.json()["email"] == "dev@example.com", r.text

        # categories
        r = await c.get("/api/questions/categories", headers=h)
        assert "Async Python" in r.json()["categories"], r.text

        # generate questions (bank fallback)
        r = await c.post("/api/questions/generate", headers=h,
                         json={"category": "Async Python", "level": "middle", "count": 3})
        assert r.status_code == 200 and r.json()["source"] == "bank", r.text
        assert len(r.json()["questions"]) == 3, r.text

        # resume upload (txt)
        resume = b"Python developer with FastAPI, PostgreSQL, Redis, Celery and Docker. Senior engineer."
        r = await c.post("/api/resumes/upload", headers=h,
                         files={"file": ("cv.txt", resume, "text/plain")})
        assert r.status_code == 201, r.text
        body = r.json()
        assert "FastAPI" in body["skills"] and body["detected_level"] in {"junior", "middle", "senior"}, body
        resume_id = body["id"]

        r = await c.get(f"/api/resumes/{resume_id}/analysis", headers=h)
        assert r.status_code == 200, r.text

        # vacancy analyze
        r = await c.post("/api/vacancies/analyze", headers=h, json={
            "title": "Senior Python Backend", "company": "Acme",
            "description": "Ищем Python backend инженера: FastAPI, PostgreSQL, Redis, "
                           "Kubernetes, Docker, gRPC. Опыт highload и микросервисов."})
        assert r.status_code == 201, r.text
        vac = r.json()
        vacancy_id = vac["id"]
        assert "FastAPI" in (vac["required_skills"] or []), vac

        # gap analysis vs resume
        r = await c.post("/api/vacancies/compare-with-resume", headers=h,
                         json={"vacancy_id": vacancy_id, "resume_id": resume_id})
        assert r.status_code == 200, r.text
        gap = r.json()
        assert 0 <= gap["match_score"] <= 100, gap
        assert isinstance(gap["missing_skills"], list), gap

        # prep roadmap
        r = await c.post("/api/vacancies/roadmap", headers=h,
                         json={"vacancy_id": vacancy_id, "resume_id": resume_id, "weeks": 3})
        assert r.status_code == 200, r.text
        assert len(r.json()["weeks"]) >= 1, r.text

        # vacancy list
        r = await c.get("/api/vacancies", headers=h)
        assert len(r.json()) == 1, r.text

        # start interview
        r = await c.post("/api/interviews/start", headers=h,
                         json={"category": "FastAPI", "level": "middle", "num_questions": 2})
        assert r.status_code == 201, r.text
        interview = r.json()
        iid = interview["id"]
        qids = [q["id"] for q in interview["questions"]]
        assert len(qids) == 2, interview

        # answer the first, then FOLLOW next_question (catches the stale-pointer bug)
        ans = ("Depends injects dependencies and resolves them per request, "
               "enabling reuse, testing via overrides and shared resources.")
        r = await c.post(f"/api/interviews/{iid}/answer", headers=h,
                         json={"question_id": qids[0], "answer": ans})
        assert r.status_code == 200, r.text
        nxt = r.json()["next_question"]
        assert nxt is not None and nxt["id"] != qids[0], r.text  # must advance

        # answer the remaining question(s) by following next_question
        last = r.json()
        while last["next_question"] is not None:
            r = await c.post(f"/api/interviews/{iid}/answer", headers=h,
                             json={"question_id": last["next_question"]["id"], "answer": ans})
            assert r.status_code == 200, r.text
            last = r.json()
        assert last["interview_completed"] is True, last
        assert last["interview_total_score"] is not None, last

        # result
        r = await c.get(f"/api/interviews/{iid}/result", headers=h)
        res = r.json()
        assert res["answered_count"] == 2 and res["status"] == "completed", res

        # history
        r = await c.get("/api/interviews/history", headers=h)
        assert len(r.json()) == 1, r.text

        # coach / ask (offline -> 'unavailable', no fabricated answer)
        r = await c.post("/api/coach/ask", headers=h,
                         json={"question": "Чем GIL мешает многопоточности?"})
        assert r.status_code == 200, r.text
        assert r.json()["source"] == "unavailable", r.text

        # coach / ask with multi-turn history (schema accepts follow-ups)
        r = await c.post("/api/coach/ask", headers=h, json={
            "question": "А если внутри него вызвать blocking I/O?",
            "history": [
                {"role": "user", "content": "Что такое event loop?"},
                {"role": "assistant", "content": "Это цикл обработки событий."},
            ]})
        assert r.status_code == 200 and r.json()["source"] == "unavailable", r.text

        # coach / ask/stream (offline -> streams the unavailable message)
        async with c.stream("POST", "/api/coach/ask/stream", headers=h,
                            json={"question": "Что такое event loop?"}) as resp:
            assert resp.status_code == 200, resp
            body = (await resp.aread()).decode("utf-8")
        assert "ANTHROPIC_API_KEY" in body, body

    print("OK: all smoke checks passed. Routes:", len([r for r in app.routes]))


if __name__ == "__main__":
    asyncio.run(main())
