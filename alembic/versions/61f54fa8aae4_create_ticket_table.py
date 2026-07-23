"""create ticket table.

Revision ID: 61f54fa8aae4
Revises: f27c6debce80
Create Date: 2026-07-19 21:34:26.762675

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel  # noqa: F401
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '61f54fa8aae4'
down_revision: Union[str, Sequence[str], None] = 'f27c6debce80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ticket",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("cohort_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("summary", JSONB, nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(
            ["session_id"],
            ["session.id"],
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_ticket_session_id"), "ticket", ["session_id"])
    op.create_index(op.f("ix_ticket_status"), "ticket", ["status"])
    op.create_index(op.f("ix_ticket_cohort_id"), "ticket", ["cohort_id"])
    op.create_index(op.f("ix_ticket_created_at"), "ticket", ["created_at"])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_ticket_created_at"), table_name="ticket")
    op.drop_index(op.f("ix_ticket_cohort_id"), table_name="ticket")
    op.drop_index(op.f("ix_ticket_status"), table_name="ticket")
    op.drop_index(op.f("ix_ticket_session_id"), table_name="ticket")

    op.drop_table("ticket")