"""Business logic for Operations tickets."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import Session, and_, or_, select

from app.models.ticket import Ticket, TicketStatus
from app.schemas.ticket import ConversationSummary, EscalationEvent
from app.services.database import database_service
from app.services.ticket_knowledge_service import ticket_knowledge_service


class TicketService:
    """Service responsible for ticket operations."""

    async def create_ticket(
        self,
        event: EscalationEvent,
        summary: ConversationSummary,
    ) -> Ticket:
        """Create a new ticket or update the existing open ticket."""
        with Session(database_service.engine) as session:

            statement = select(Ticket).where(
                Ticket.session_id == event.session_id,
                Ticket.status == TicketStatus.OPEN,
            )

            ticket = session.exec(statement).first()

            # Update existing open ticket
            if ticket:
                ticket.summary = summary.summary

                session.add(ticket)
                session.commit()
                session.refresh(ticket)

                return ticket

            # Otherwise create a new ticket
            ticket = Ticket(
                id=str(uuid.uuid4()),
                session_id=event.session_id,
                cohort_id=event.cohort_id,
                status=TicketStatus.OPEN,
                summary=summary.summary,
            )

            session.add(ticket)
            session.commit()
            session.refresh(ticket)

            return ticket

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        """Retrieve a ticket by its ID."""
        with Session(database_service.engine) as session:
            return session.get(Ticket, ticket_id)

    async def list_tickets(
        self,
        status: TicketStatus | None = None,
        cohort_id: str | None = None,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
        limit: int = 20,
    ) -> list[Ticket]:
        """Retrieve tickets with optional filters."""
        with Session(database_service.engine) as session:

            statement = select(Ticket)

            if status:
                statement = statement.where(Ticket.status == status)

            if cohort_id:
                statement = statement.where(Ticket.cohort_id == cohort_id)

            if cursor_created_at and cursor_id:
                statement = statement.where(
                    or_(
                        Ticket.created_at < cursor_created_at,
                        and_(
                            Ticket.created_at == cursor_created_at,
                            Ticket.id < cursor_id,
                        ),
                    )
                )

            statement = (
                statement
                .order_by(Ticket.created_at.desc(), Ticket.id.desc(),)
                .limit(limit)
            )

            return list(session.exec(statement).all())

    async def resolve_ticket(
        self,
        ticket_id: str,
        resolution_note: str,
    ) -> Ticket:
        """Resolve an open ticket."""
        with Session(database_service.engine) as session:

            ticket = session.get(Ticket, ticket_id)

            if ticket is None:
                raise HTTPException(
                    status_code=404,
                    detail="Ticket not found",
                )

            if ticket.status == TicketStatus.RESOLVED:
                raise HTTPException(
                    status_code=400,
                    detail="Ticket is already resolved",
                )

            ticket.status = TicketStatus.RESOLVED
            ticket.resolution_note = resolution_note
            ticket.resolved_at = datetime.now(UTC)

            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_knowledge_service.ingest_resolved_ticket(ticket)

            return ticket


ticket_service = TicketService()