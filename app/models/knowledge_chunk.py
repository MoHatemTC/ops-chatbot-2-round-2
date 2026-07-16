"""
SQLModel table for F1.1 knowledge base chunks — one row per embedded chunk,
with metadata (title, source, type, cohort) and content_hash for
update-not-duplicate lookups. Table + pgvector extension are created by
alembic/versions/f27c6debce80_create_knowledge_chunk_table.py, which
imports EMBEDDING_DIM from this file so the migration and the ORM model
can never silently drift apart on vector dimension.
"""
 
from __future__ import annotations
 
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field
 
from app.core.config import settings
from app.models.base import BaseModel
 
# Known OpenAI embedding model -> output dimension. Extend if the team
# adopts a different embedder.
_KNOWN_EMBEDDING_DIMS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}
 
 
def _resolve_embedding_dim(model_name: str) -> int:
    """Look up the output dimension for the configured embedder model."""
    return _KNOWN_EMBEDDING_DIMS.get(model_name, 1536)
 
 
EMBEDDING_DIM = _resolve_embedding_dim(settings.LONG_TERM_MEMORY_EMBEDDER_MODEL)
 
 
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