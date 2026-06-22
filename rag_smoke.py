"""Offline RAG smoke test. First run downloads the embedding model (~hundreds MB).
Run: python rag_smoke.py
"""
import asyncio
import os

os.environ["ANTHROPIC_API_KEY"] = ""  # force offline (snippets + sources)

from app.services.rag import service as rag_service

# (query, expected top source file)
CASES = [
    ("Чем asyncio.gather отличается от create_task?", "async-event-loop.md"),
    ("Как избежать проблемы N+1 в SQLAlchemy?", "sqlalchemy-nplus1.md"),
    ("Что такое cache-aside и зачем TTL?", "redis-caching.md"),
    ("Почему GIL мешает многопоточности?", "python-gil.md"),
    ("Когда использовать selectinload vs joinedload?", "sqlalchemy-nplus1.md"),
]


async def main() -> None:
    passed = 0
    for query, expected in CASES:
        answer, source, sources = await rag_service.answer(query)
        assert sources, f"no sources returned for: {query}"
        top = sources[0]
        ok = top.source == expected
        passed += ok
        print(f"{'OK ' if ok else 'MISS'} | {query}")
        print(f"      top=[{top.source}] score={top.score} (expected {expected})")
    print(f"\nRetrieval relevance: {passed}/{len(CASES)} top-1 correct")
    assert passed >= len(CASES) - 1, "retrieval quality too low"
    print("OK: RAG retrieval works offline with sources.")


if __name__ == "__main__":
    asyncio.run(main())
