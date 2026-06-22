"""Lazy in-memory Qdrant index over the knowledge base (fastembed embeddings)."""
import logging
import threading

from app.core.config import settings
from app.services.rag.corpus import load_chunks

logger = logging.getLogger(__name__)

_COLLECTION = "kb"


class RagIndex:
    """Builds the vector index on first use; thread-safe and process-local."""

    def __init__(self) -> None:
        self._client = None
        self._lock = threading.Lock()
        self._chunk_count = 0

    def _build(self) -> None:
        from qdrant_client import QdrantClient

        client = QdrantClient(":memory:")
        client.set_model(settings.rag_embed_model)

        chunks = load_chunks()
        client.add(
            collection_name=_COLLECTION,
            documents=[c["text"] for c in chunks],
            metadata=[{"title": c["title"], "source": c["source"]} for c in chunks],
            ids=list(range(len(chunks))),
        )
        self._client = client
        self._chunk_count = len(chunks)
        logger.info("RAG index built: %d chunks via %s", len(chunks), settings.rag_embed_model)

    def ensure_built(self) -> None:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._build()

    def search(self, query: str, k: int) -> list[dict]:
        self.ensure_built()
        hits = self._client.query(
            collection_name=_COLLECTION, query_text=query, limit=k
        )
        return [
            {
                "title": (h.metadata or {}).get("title", ""),
                "source": (h.metadata or {}).get("source", ""),
                "text": h.document or "",
                "score": float(h.score),
            }
            for h in hits
        ]


# Module-level singleton.
rag_index = RagIndex()
