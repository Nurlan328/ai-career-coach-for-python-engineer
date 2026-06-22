VACANCY = (
    "Ищем Senior Python backend инженера: FastAPI, PostgreSQL, Redis, Kubernetes, "
    "Docker, gRPC. Опыт highload, микросервисов и CI/CD."
)
RESUME = b"Python backend: FastAPI, PostgreSQL, Redis, Docker, asyncio. Senior."


async def test_gap_analysis_and_roadmap(client, headers):
    r = await client.post(
        "/api/resumes/upload",
        headers=headers,
        files={"file": ("cv.txt", RESUME, "text/plain")},
    )
    resume_id = r.json()["id"]

    r = await client.post(
        "/api/vacancies/analyze",
        headers=headers,
        json={"title": "Senior BE", "description": VACANCY},
    )
    assert r.status_code == 201, r.text
    vacancy = r.json()
    assert "FastAPI" in (vacancy["required_skills"] or [])
    vacancy_id = vacancy["id"]

    r = await client.post(
        "/api/vacancies/compare-with-resume",
        headers=headers,
        json={"vacancy_id": vacancy_id, "resume_id": resume_id},
    )
    gap = r.json()
    assert 0 <= gap["match_score"] <= 100
    assert "Kubernetes" in gap["missing_skills"] or "gRPC" in gap["missing_skills"]

    r = await client.post(
        "/api/vacancies/roadmap",
        headers=headers,
        json={"vacancy_id": vacancy_id, "resume_id": resume_id, "weeks": 3},
    )
    assert len(r.json()["weeks"]) >= 1


async def test_compare_requires_owned_entities(client, headers):
    r = await client.post(
        "/api/vacancies/compare-with-resume",
        headers=headers,
        json={"vacancy_id": 9999, "resume_id": 9999},
    )
    assert r.status_code == 404
