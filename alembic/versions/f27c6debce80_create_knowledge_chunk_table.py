"""create knowledge chunk table.
 
Revision ID: f27c6debce80
Revises: b25d38b0cd7c
Create Date: 2026-07-16 00:19:03.951071
 
"""
 
from typing import Sequence, Union
 
import sqlalchemy as sa
import sqlmodel  # noqa: F401
from pgvector.sqlalchemy import Vector
 
from alembic import op
from app.models.knowledge_chunk import EMBEDDING_DIM
 
# revision identifiers, used by Alembic.
revision: str = "f27c6debce80"
down_revision: Union[str, Sequence[str], None] = "b25d38b0cd7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
 
 
def upgrade() -> None:
    """Upgrade schema."""
 
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
 
    # Create the knowledgechunk table
    op.create_table(
        "knowledgechunk",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("cohort", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        # Dimension imported from the model rather than hardcoded here, so
        # the table definition and the ORM model can never silently drift
        # apart if the configured embedder model ever changes.
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
 
    op.create_index(
        "ix_knowledgechunk_document_id",
        "knowledgechunk",
        ["document_id"],
    )
 
    op.create_index(
        "ix_knowledgechunk_cohort",
        "knowledgechunk",
        ["cohort"],
    )
 
    op.create_index(
        "ix_knowledgechunk_content_hash",
        "knowledgechunk",
        ["content_hash"],
    )
 
 
def downgrade() -> None:
    """Downgrade schema."""
 
    op.drop_index("ix_knowledgechunk_content_hash", table_name="knowledgechunk")
    op.drop_index("ix_knowledgechunk_cohort", table_name="knowledgechunk")
    op.drop_index("ix_knowledgechunk_document_id", table_name="knowledgechunk")
 
    op.drop_table("knowledgechunk")