"""API endpoints for Operations tickets."""

import base64
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.config import settings
from app.core.limiter import limiter
from app.models.ticket import TicketStatus
from app.api.v1.auth import get_current_session
from app.models.session import Session
from app.schemas.ticket import (
    ResolveTicketRequest,
    TicketListResponse,
    TicketResponse,
)
from app.services.ticket_service import ticket_service

router = APIRouter()


@router.get("/{ticket_id}", response_model=TicketResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["tickets"][0])
async def get_ticket(
    request: Request,
    ticket_id: str,
    session: Session = Depends(get_current_session),
):
    """Retrieve a ticket by its ID."""
    ticket = await ticket_service.get_ticket(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return ticket


@router.get("/", response_model=TicketListResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["tickets"][0])
async def list_tickets(
    request: Request,
    session: Session = Depends(get_current_session),
    status: TicketStatus | None = None,
    cohort_id: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
):
    """Retrieve tickets with optional filters and opaque cursor pagination."""

    cursor_created_at = None
    cursor_id = None

    if cursor:
        try:
            decoded = base64.b64decode(cursor.encode()).decode()
            created_at_str, cursor_id = decoded.split("|")
            cursor_created_at = datetime.fromisoformat(created_at_str)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid cursor",
            )

    tickets = await ticket_service.list_tickets(
        status=status,
        cohort_id=cohort_id,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
        limit=limit + 1,   # Fetch one extra row
    )

    next_cursor = None

    if len(tickets) > limit:
        last_ticket = tickets[limit - 1]

        raw_cursor = (
            f"{last_ticket.created_at.isoformat()}|{last_ticket.id}"
        )

        next_cursor = base64.b64encode(
            raw_cursor.encode()
        ).decode()

        tickets = tickets[:limit]

    return TicketListResponse(
        tickets=tickets,
        next_cursor=next_cursor,
    )

@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["tickets"][0])
async def resolve_ticket(
    request: Request,
    ticket_id: str,
    payload: ResolveTicketRequest,
    session: Session = Depends(get_current_session),
):
    """Resolve an operations ticket."""
    return await ticket_service.resolve_ticket(
        ticket_id=ticket_id,
        resolution_note=payload.resolution_note,
    )


