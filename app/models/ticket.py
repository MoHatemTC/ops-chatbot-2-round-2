"""Operations ticket database model.

This module defines the SQLModel used to store escalated conversations
that require human intervention. Each ticket stores the conversation
summary, its current status, and resolution details, while enforcing
the one-open-ticket-per-session rule.
"""



from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base import BaseModel


class TicketStatus(str, Enum):
    """Possible states of a ticket."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class Ticket(BaseModel, table=True):
    """Operations ticket created when a conversation is escalated."""

    id: str = Field(primary_key=True)

    session_id: str = Field(
        foreign_key="session.id",
        index=True,
    )

    cohort_id: str = Field(index=True)

    status: TicketStatus = Field(
        default=TicketStatus.OPEN,
        index=True,
    )

    # Stores the conversation summary losslessly.
    summary: dict[str, object] = Field(
    sa_column=Column(JSONB, nullable=False)
    )

    # Added by an Ops engineer when resolving the ticket.
    resolution_note: Optional[str] = None

    # Timestamp of resolution.
    resolved_at: Optional[datetime] = None