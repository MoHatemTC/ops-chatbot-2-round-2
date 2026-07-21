"""Tests for the TicketService business logic.

These tests verify ticket creation, retrieval, update, resolution,
and listing behavior using the test database.
"""

import pytest
from fastapi import HTTPException

from app.models.ticket import TicketStatus
from app.schemas.ticket import ConversationSummary, EscalationEvent
from app.services.ticket_service import TicketService


@pytest.mark.asyncio
async def test_create_ticket_creates_new_ticket():
    """Verify that creating a ticket stores a new open ticket."""
    service = TicketService()

    event = EscalationEvent(
        session_id="session-1",
        cohort_id="cohort-a",
    )

    summary = ConversationSummary(
        summary={"problem": "login failed"},
    )

    ticket = await service.create_ticket(event, summary)

    assert ticket.session_id == "session-1"
    assert ticket.cohort_id == "cohort-a"
    assert ticket.status == TicketStatus.OPEN
    assert ticket.summary == {"problem": "login failed"}


@pytest.mark.asyncio
async def test_create_ticket_updates_existing_open_ticket():
    """Verify that an existing open ticket is updated instead of recreated."""
    service = TicketService()

    event = EscalationEvent(
        session_id="session-1",
        cohort_id="cohort-a",
    )

    first = ConversationSummary(summary={"text": "first"})
    second = ConversationSummary(summary={"text": "updated"})

    ticket1 = await service.create_ticket(event, first)
    ticket2 = await service.create_ticket(event, second)

    assert ticket1.id == ticket2.id
    assert ticket2.summary == {"text": "updated"}


@pytest.mark.asyncio
async def test_get_ticket_returns_ticket():
    """Verify that a ticket can be retrieved by its ID."""
    service = TicketService()

    event = EscalationEvent(
        session_id="session-2",
        cohort_id="cohort-a",
    )

    summary = ConversationSummary(summary={"text": "hello"})

    created = await service.create_ticket(event, summary)

    ticket = await service.get_ticket(created.id)

    assert ticket is not None
    assert ticket.id == created.id


@pytest.mark.asyncio
async def test_get_ticket_returns_none_for_missing_ticket():
    """Verify that requesting an unknown ticket returns None."""
    service = TicketService()

    ticket = await service.get_ticket("missing-id")

    assert ticket is None


@pytest.mark.asyncio
async def test_resolve_ticket_marks_ticket_resolved():
    """Verify that resolving a ticket updates its status and resolution fields."""
    service = TicketService()

    event = EscalationEvent(
        session_id="session-1",
        cohort_id="cohort-a",
    )

    summary = ConversationSummary(
        summary={"problem": "login failed"},
    )

    ticket = await service.create_ticket(event, summary)

    resolved = await service.resolve_ticket(
        ticket.id,
        "Reset the user's password.",
    )

    assert resolved.id == ticket.id
    assert resolved.status == TicketStatus.RESOLVED
    assert resolved.resolution_note == "Reset the user's password."
    assert resolved.resolved_at is not None


@pytest.mark.asyncio
async def test_resolve_ticket_missing_ticket_raises_404():
    """Verify resolving a nonexistent ticket raises a 404."""
    service = TicketService()

    with pytest.raises(HTTPException) as exc:
        await service.resolve_ticket(
            "does-not-exist",
            "Anything",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Ticket not found"


@pytest.mark.asyncio
async def test_resolve_ticket_already_resolved_raises_400():
    """Verify an already resolved ticket cannot be resolved again."""
    service = TicketService()

    event = EscalationEvent(
        session_id="session-1",
        cohort_id="cohort-a",
    )

    summary = ConversationSummary(
        summary={"problem": "login failed"},
    )

    ticket = await service.create_ticket(event, summary)

    await service.resolve_ticket(
        ticket.id,
        "Initial resolution.",
    )

    with pytest.raises(HTTPException) as exc:
        await service.resolve_ticket(
            ticket.id,
            "Second resolution.",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Ticket is already resolved"


@pytest.mark.asyncio
async def test_list_tickets_returns_all():
    """Verify listing tickets returns all created tickets."""
    service = TicketService()

    await service.create_ticket(
        EscalationEvent(session_id="session-1", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "one"}),
    )

    await service.create_ticket(
        EscalationEvent(session_id="session-2", cohort_id="cohort-b"),
        ConversationSummary(summary={"text": "two"}),
    )

    tickets = await service.list_tickets()

    assert len(tickets) == 2


@pytest.mark.asyncio
async def test_list_tickets_filters_by_status():
    """Verify filtering by ticket status."""
    service = TicketService()

    ticket = await service.create_ticket(
        EscalationEvent(session_id="session-1", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "one"}),
    )

    await service.create_ticket(
        EscalationEvent(session_id="session-2", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "two"}),
    )

    await service.resolve_ticket(ticket.id, "Resolved")

    tickets = await service.list_tickets(status=TicketStatus.OPEN)

    assert len(tickets) == 1
    assert tickets[0].status == TicketStatus.OPEN


@pytest.mark.asyncio
async def test_list_tickets_filters_by_cohort():
    """Verify filtering by cohort."""
    service = TicketService()

    await service.create_ticket(
        EscalationEvent(session_id="session-1", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "one"}),
    )

    await service.create_ticket(
        EscalationEvent(session_id="session-2", cohort_id="cohort-b"),
        ConversationSummary(summary={"text": "two"}),
    )

    tickets = await service.list_tickets(cohort_id="cohort-a")

    assert len(tickets) == 1
    assert tickets[0].cohort_id == "cohort-a"


@pytest.mark.asyncio
async def test_list_tickets_filters_by_status_and_cohort():
    """Verify filtering by both status and cohort."""
    service = TicketService()

    ticket = await service.create_ticket(
        EscalationEvent(session_id="session-1", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "one"}),
    )

    await service.create_ticket(
        EscalationEvent(session_id="session-2", cohort_id="cohort-b"),
        ConversationSummary(summary={"text": "two"}),
    )

    await service.resolve_ticket(ticket.id, "Done")

    tickets = await service.list_tickets(
        status=TicketStatus.RESOLVED,
        cohort_id="cohort-a",
    )

    assert len(tickets) == 1
    assert tickets[0].status == TicketStatus.RESOLVED
    assert tickets[0].cohort_id == "cohort-a"


@pytest.mark.asyncio
async def test_list_tickets_respects_limit():
    """Verify the limit parameter restricts returned tickets."""
    service = TicketService()

    for i in range(5):
        await service.create_ticket(
            EscalationEvent(
                session_id=f"session-{i}",
                cohort_id="cohort-a",
            ),
            ConversationSummary(summary={"text": str(i)}),
        )

    tickets = await service.list_tickets(limit=3)

    assert len(tickets) == 3


@pytest.mark.asyncio
async def test_list_tickets_cursor_pagination():
    """Verify cursor pagination returns tickets after the cursor."""
    service = TicketService()

    await service.create_ticket(
        EscalationEvent(session_id="session-1", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "one"}),
    )

    await service.create_ticket(
        EscalationEvent(session_id="session-2", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "two"}),
    )

    await service.create_ticket(
        EscalationEvent(session_id="session-3", cohort_id="cohort-a"),
        ConversationSummary(summary={"text": "three"}),
    )

    all_tickets = await service.list_tickets()

    cursor = all_tickets[0]

    remaining = await service.list_tickets(
        cursor_created_at=cursor.created_at,
        cursor_id=cursor.id,
    )

    assert len(remaining) == 2
    assert all(ticket.id != cursor.id for ticket in remaining)