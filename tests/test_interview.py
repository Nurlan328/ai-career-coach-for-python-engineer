async def test_interview_advances_and_completes(client, headers):
    r = await client.post(
        "/api/interviews/start",
        headers=headers,
        json={"category": "FastAPI", "level": "middle", "num_questions": 2},
    )
    assert r.status_code == 201, r.text
    interview = r.json()
    iid = interview["id"]
    q0 = interview["questions"][0]["id"]

    ans = "Depends injects dependencies per request, enabling reuse and testing."
    r = await client.post(
        f"/api/interviews/{iid}/answer",
        headers=headers,
        json={"question_id": q0, "answer": ans},
    )
    assert r.status_code == 200, r.text
    nxt = r.json()["next_question"]
    # Regression guard: the interview must advance to a different question.
    assert nxt is not None and nxt["id"] != q0

    r = await client.post(
        f"/api/interviews/{iid}/answer",
        headers=headers,
        json={"question_id": nxt["id"], "answer": ans},
    )
    assert r.json()["interview_completed"] is True

    r = await client.get(f"/api/interviews/{iid}/result", headers=headers)
    result = r.json()
    assert result["answered_count"] == 2
    assert result["status"] == "completed"


async def test_interview_history(client, headers):
    await client.post(
        "/api/interviews/start",
        headers=headers,
        json={"category": "Async Python", "level": "junior", "num_questions": 1},
    )
    r = await client.get("/api/interviews/history", headers=headers)
    assert len(r.json()) == 1
