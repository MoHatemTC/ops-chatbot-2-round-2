"""Knowledge Base storage and chunking utilities.

This module provides document chunking and ingestion logic for the
Knowledge Base, including orchestration for embeddings and storage.
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

DEFAULT_CHUNK_SIZE = 500  # characters
DEFAULT_OVERLAP = 75

# Type aliases for the injectable storage functions.
GetHashFn = Callable[[str], Optional[str]]
DeleteFn = Callable[[str], None]
EmbedFn = Callable[[str], list[float]]
StoreFn = Callable[[Document, list[tuple[Chunk, list[float]]]], None]

# Reuses the existing long-term-memory embedder setting/model.
_embeddings_client = OpenAIEmbeddings(
    model=settings.LONG_TERM_MEMORY_EMBEDDER_MODEL,
    api_key=settings.OPENAI_API_KEY,
)

# Material types whose content is naturally a sequence of discrete blocks
# (one FAQ = one Q/A block, one schedule = one session/entry) rather than
# continuous prose. Both benefit from block-aware chunking so a chunk never
# splits a single Q/A pair or a single session entry across two chunks.
_BLOCK_STRUCTURED_TYPES = {MaterialType.FAQ, MaterialType.SCHEDULE}


def chunk_document(document: Document) -> list[Chunk]:
    """Split a document into chunks.

    Uses a structure-aware strategy depending on the material type.
    """
    if document.metadata.type in _BLOCK_STRUCTURED_TYPES:
        pieces = _chunk_by_blank_line_blocks(document.raw_text)
    else:
        pieces = _chunk_fixed_size(
            document.raw_text,
            DEFAULT_CHUNK_SIZE,
            DEFAULT_OVERLAP,
        )

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
    """Split text into blank-line-separated blocks.

    Falls back to fixed-size chunking when the text has no clear block structure.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return (
        blocks
        if blocks
        else _chunk_fixed_size(text, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP)
    )


def _chunk_fixed_size(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping fixed-size chunks."""
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


def ingest_document(
    document: Document,
    *,
    get_existing_hash: GetHashFn | None = None,
    delete_chunks: DeleteFn | None = None,
    embed: EmbedFn | None = None,
    store_chunks: StoreFn | None = None,
) -> str:
    """Insert-or-replace a document's chunks in pgvector.

    Returns "inserted", "updated", or "skipped" depending on whether
    the document is new, changed, or already up to date.
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
    embedded = [(chunk, embed(chunk.text)) for chunk in chunks]
    store_chunks(document, embedded)

    return "updated" if existing_hash is not None else "inserted"


def _get_existing_content_hash(document_id: str) -> str | None:
    """Look up the stored content hash for a document.

    Returns ``None`` if the document has never been ingested.
    All chunks belonging to the same document share the same content hash.
    """
    with Session(database_service.engine) as session:
        statement = (
            select(KnowledgeChunk.content_hash)
            .where(KnowledgeChunk.document_id == document_id)
            .limit(1)
        )
        return session.exec(statement).first()


def _delete_chunks(document_id: str) -> None:
    """Delete all chunks belonging to a document.

    Used before inserting updated content.
    """
    with Session(database_service.engine) as session:
        session.exec(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.document_id == document_id
            )
        )
        session.commit()


def _embed(text: str) -> list[float]:
    """Generate an embedding vector for text.

    Uses the configured OpenAI embedding model.
    """
    return _embeddings_client.embed_query(text)


def _store_chunks(
    document: Document,
    embedded_chunks: list[tuple[Chunk, list[float]]],
) -> None:
    """Store embedded chunks in the KnowledgeChunk table."""
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