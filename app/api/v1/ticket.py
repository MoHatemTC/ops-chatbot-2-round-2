"""API endpoints for Operations tickets."""


from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.config import settings
from app.core.limiter import limiter
from app.models.ticket import TicketStatus
from app.api.v1.auth import get_current_session
from app.models.session import Session
from app.schemas.ticket import (
    ResolveTicketRequest,
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


@router.get("/", response_model=list[TicketResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["tickets"][0])
async def list_tickets(
    request: Request,
    session: Session = Depends(get_current_session),
    status: TicketStatus | None = None,
    cohort_id: str | None = None,
    cursor_created_at: datetime | None = None,
    cursor_id: str | None = None,
    limit: int = 20,
):
    """Retrieve tickets with optional filters."""
    return await ticket_service.list_tickets(
       status=status,
       cohort_id=cohort_id,
       cursor_created_at=cursor_created_at,
       cursor_id=cursor_id,
       limit=limit,
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


