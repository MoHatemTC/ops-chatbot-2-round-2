"""
Chunking (structure-aware: FAQs/schedules split on blank-line blocks,
onboarding/program docs use fixed-size + overlap) and storage (insert/
update/skip via content-hash comparison) for the F1.1 ingestion pipeline.
 
Storage functions are wired to database_service (app/services/database.py)
and KnowledgeChunk (app/models/knowledge_chunk.py), with the corresponding
table created by alembic/versions/f27c6debce80_create_knowledge_chunk_table.py.
 
Embeddings are batched per document (one embed_documents() call, not one
per chunk) via langchain_openai.OpenAIEmbeddings, and the vector column's
dimension is derived from the configured embedder model rather than
hardcoded (see EMBEDDING_DIM in knowledge_chunk.py).
 
Open items still worth a quick confirm from your mentor (not blockers):
- app/models/knowledge_chunk.py as a new file — ownership/location.
- Reusing settings.LONG_TERM_MEMORY_EMBEDDER_MODEL for KB embeddings vs.
  adding a KB-specific setting.
"""
 
from __future__ import annotations
 
import re
from typing import Callable, Optional
 
from langchain_openai import OpenAIEmbeddings
from sqlmodel import Session, delete, select
 
from app.core.config import settings
from app.models.knowledge_chunk import KnowledgeChunk
from app.schemas.knowledge import Chunk, Document, MaterialType
from app.services.database import database_service
 
DEFAULT_CHUNK_SIZE = 500  # characters — revisit once real tokenizer is known
DEFAULT_OVERLAP = 75
 
# Type aliases for the injectable storage functions.
# EmbedFn is now BATCH: takes all chunk texts for one document, returns one
# vector per text, in the same order — a single API call instead of N.
GetHashFn = Callable[[str], Optional[str]]
DeleteFn = Callable[[str], None]
EmbedFn = Callable[[list[str]], list[list[float]]]
StoreFn = Callable[[Document, list[tuple[Chunk, list[float]]]], None]
 
# Reuses the existing long-term-memory embedder setting/model — see open
# question above before assuming this is final.
_embeddings_client = OpenAIEmbeddings(
    model=settings.LONG_TERM_MEMORY_EMBEDDER_MODEL,
    api_key=settings.OPENAI_API_KEY,
)
 
 
# ---------------------------------------------------------------------------
# Chunking — pure functions, no DB/embedding dependency, testable right now.
# ---------------------------------------------------------------------------
 
# Material types whose content is naturally a sequence of discrete blocks
# (one FAQ = one Q/A block, one schedule = one session/entry) rather than
# continuous prose. Both benefit from block-aware chunking so a chunk never
# splits a single Q/A pair or a single session entry across two chunks.
_BLOCK_STRUCTURED_TYPES = {MaterialType.FAQ, MaterialType.SCHEDULE}
 
 
def chunk_document(document: Document) -> list[Chunk]:
    """Split a Document's raw_text into Chunks, dispatching to a
    structure-aware strategy per material type."""
    if document.metadata.type in _BLOCK_STRUCTURED_TYPES:
        pieces = _chunk_by_blank_line_blocks(document.raw_text)
    else:
        pieces = _chunk_fixed_size(document.raw_text, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP)
 
    return [
        Chunk(
            id=f"{document.id}:{i}",
            document_id=document.id,
            index=i,
            text=piece,
            metadata=document.metadata,
        )
        for i, piece in enumerate(pieces)
    ]
 
 
def _chunk_by_blank_line_blocks(text: str) -> list[str]:
    """Split on blank-line-separated blocks (e.g. one Q&A pair per block).
    Falls back to fixed-size chunking if the text has no clear block structure."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return blocks if blocks else _chunk_fixed_size(text, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP)
 
 
def _chunk_fixed_size(text: str, size: int, overlap: int) -> list[str]:
    if size <= overlap:
        raise ValueError("chunk size must be greater than overlap")
 
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end - overlap
    return chunks
 
 
# ---------------------------------------------------------------------------
# Storage — now wired to the real DB via database_service + KnowledgeChunk.
# ---------------------------------------------------------------------------
 
def ingest_document(
    document: Document,
    *,
    get_existing_hash: GetHashFn | None = None,
    delete_chunks: DeleteFn | None = None,
    embed: EmbedFn | None = None,
    store_chunks: StoreFn | None = None,
) -> str:
    """Insert-or-replace a document's chunks in pgvector (update-not-duplicate).
 
    Returns "inserted", "updated", or "skipped" — useful both for logging
    and for asserting behavior directly in tests.
 
    The four keyword arguments default to the real module-level functions
    above. Tests pass in-memory fakes instead so the insert/update/skip
    orchestration is verified independently of a live DB connection — see
    tests/test_ingest_document.py.
    """
    get_existing_hash = get_existing_hash or _get_existing_content_hash
    delete_chunks = delete_chunks or _delete_chunks
    embed = embed or _embed
    store_chunks = store_chunks or _store_chunks
 
    existing_hash = get_existing_hash(document.id)
 
    if existing_hash == document.content_hash:
        return "skipped"
 
    if existing_hash is not None:
        delete_chunks(document.id)
 
    chunks = chunk_document(document)
    vectors = embed([chunk.text for chunk in chunks])  # one batched call, not one per chunk
    embedded = list(zip(chunks, vectors))
    store_chunks(document, embedded)
 
    return "updated" if existing_hash is not None else "inserted"
 
 
def _get_existing_content_hash(document_id: str) -> str | None:
    """Look up the stored content_hash for document_id, or None if the
    document has never been ingested. Any existing row's hash is
    representative since all chunks of one document share one content_hash."""
    with Session(database_service.engine) as session:
        statement = (
            select(KnowledgeChunk.content_hash)
            .where(KnowledgeChunk.document_id == document_id)
            .limit(1)
        )
        return session.exec(statement).first()
 
 
def _delete_chunks(document_id: str) -> None:
    """Delete all existing chunk rows for document_id (used before
    re-inserting updated content)."""
    with Session(database_service.engine) as session:
        session.exec(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
        session.commit()
 
 
def _embed(texts: list[str]) -> list[list[float]]:
    """Call the platform's embedding model via langchain_openai, batched:
    one API call for all of a document's chunks instead of one per chunk."""
    return _embeddings_client.embed_documents(texts)
 
 
def _store_chunks(document: Document, embedded_chunks: list[tuple[Chunk, list[float]]]) -> None:
    """Insert (chunk, vector, metadata) rows into pgvector via KnowledgeChunk."""
    with Session(database_service.engine) as session:
        for chunk, vector in embedded_chunks:
            session.add(
                KnowledgeChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    index=chunk.index,
                    text=chunk.text,
                    title=chunk.metadata.title,
                    source=chunk.metadata.source,
                    type=chunk.metadata.type.value,
                    cohort=chunk.metadata.cohort,
                    content_hash=document.content_hash,
                    embedding=vector,
                )
            )
        session.commit()