"""
Unified schema contracts for the F1.1 knowledge base ingestion pipeline:
MaterialType, DocumentMetadata, Document, Chunk, and content hashing used
by update-not-duplicate ingestion.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class MaterialType(str, Enum):
    """Approved material types in scope for Sprint 1 (F1.1)."""

    FAQ = "faq"
    ONBOARDING = "onboarding"
    SCHEDULE = "schedule"
    PROGRAM_DOC = "program_doc"


def compute_content_hash(text: str) -> str:
    """Stable content hash used to detect changed materials on re-ingestion.

    Update-not-duplicate logic compares this against the stored hash for a
    document id: same hash -> skip, different hash -> replace, missing -> insert.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentMetadata(BaseModel):
    """Metadata carried by a Document and copied onto every Chunk derived from it.

    Required fields per the task spec: title, source, type, cohort.
    """

    title: str
    source: str  # file path (or URL) the material was ingested from
    type: MaterialType
    cohort: str
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Document(BaseModel):
    """Unified shape every loader must return, regardless of source format.

    `id` is the stable identifier used for update-not-duplicate lookups.
    """

    id: str
    raw_text: str
    metadata: DocumentMetadata
    content_hash: str

    @classmethod
    def create(cls, id: str, raw_text: str, metadata: DocumentMetadata) -> "Document":
        """Convenience constructor that computes content_hash from raw_text,
        so loaders never have to remember to hash manually."""
        return cls(
            id=id,
            raw_text=raw_text,
            metadata=metadata,
            content_hash=compute_content_hash(raw_text),
        )


class Chunk(BaseModel):
    """A single retrievable unit stored in pgvector.

    Metadata is duplicated onto the chunk (not just the parent document)
    because retrieval and cohort-scoping happen at chunk granularity.
    """

    id: str  # f"{document_id}:{index}"
    document_id: str
    index: int
    text: str
    metadata: DocumentMetadata