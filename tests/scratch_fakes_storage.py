"""
In-memory stand-ins for the pgvector table and embedding client, used by
tests/test_ingest_document.py to exercise app/kb/store.py's
ingest_document() insert/update/skip logic without needing a live database
or real OpenAI API calls in the test suite. This is intentionally kept
alongside the tests as fast, deterministic unit-test coverage even after
the real backend exists — integration tests against a real test DB can be
added separately without replacing this.
"""
 
from __future__ import annotations
 
from app.schemas.knowledge import Chunk, Document
 
 
class InMemoryKnowledgeStore:
    """A fake pgvector table: document_id -> (content_hash, chunks).
 
    Mirrors exactly the shape ingest_document() expects from
    get_existing_hash / delete_chunks / store_chunks, so it can be passed
    straight in as those three keyword arguments.
    """
 
    def __init__(self) -> None:
        self._hashes: dict[str, str] = {}
        self._chunks: dict[str, list[Chunk]] = {}
        self.embed_call_count = 0
 
    def get_existing_hash(self, document_id: str) -> str | None:
        return self._hashes.get(document_id)
 
    def delete_chunks(self, document_id: str) -> None:
        self._hashes.pop(document_id, None)
        self._chunks.pop(document_id, None)
 
    def store_chunks(self, document: Document, embedded_chunks: list[tuple[Chunk, list[float]]]) -> None:
        self._hashes[document.id] = document.content_hash
        self._chunks[document.id] = [chunk for chunk, _vector in embedded_chunks]
 
    def fake_embed(self, texts: list[str]) -> list[list[float]]:
        """Deterministic fake batch embedding — one call regardless of how
        many texts are passed, so tests can assert batching actually happens
        (embed_call_count increments once per ingest_document call, not once
        per chunk)."""
        self.embed_call_count += 1
        return [[float(len(t)), float(t.count(" ")), 1.0] for t in texts]
 
    def chunks_for(self, document_id: str) -> list[Chunk]:
        return self._chunks.get(document_id, [])