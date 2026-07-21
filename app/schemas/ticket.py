"""Pydantic schemas used by the ticketing system."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.ticket import TicketStatus


class EscalationEvent(BaseModel):
    """Information required to create or update an operations ticket."""

    session_id: str
    cohort_id: str


class ConversationSummary(BaseModel):
    """Summary of the escalated conversation."""

    summary: dict


class TicketResponse(BaseModel):
    """Response returned for ticket operations."""

    id: str
    session_id: str
    cohort_id: str
    status: TicketStatus
    summary: dict
    resolution_note: Optional[str] = None
    resolved_at: Optional[datetime] = None


class ResolveTicketRequest(BaseModel):
    """Request body for resolving a ticket."""

    resolution_note: str