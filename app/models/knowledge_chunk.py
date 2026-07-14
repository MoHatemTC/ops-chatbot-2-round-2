"""Knowledge Chunk database model.

This module defines the SQLModel used to store document chunks,
their embeddings, and metadata in the Knowledge Base.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field

from app.models.base import BaseModel

EMBEDDING_DIM = 1536  # text-embedding-3-small


class KnowledgeChunk(BaseModel, table=True):
    """One retrievable chunk of an ingested material, with its embedding.

    `document_id` groups all chunks belonging to the same source Document
    (see app/schemas/knowledge.py) — update-not-duplicate ingestion deletes
    and re-inserts all rows sharing a document_id when content changes.
    """
    id: str = Field(primary_key=True)  # f"{document_id}:{index}"
    document_id: str = Field(index=True)
    index: int
    text: str

    # Metadata copied from DocumentMetadata — flattened onto the row since
    # SQLModel doesn't easily nest a Pydantic sub-model into a table column.
    title: str
    source: str
    type: str  # MaterialType.value
    cohort: str = Field(index=True)  # indexed: retrieval always filters by cohort

    content_hash: str = Field(index=True)  # used by update-not-duplicate lookups
    embedding: list[float] = Field(sa_column=Column(Vector(EMBEDDING_DIM)))