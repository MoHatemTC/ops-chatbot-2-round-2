"""API-level tests for the Operations ticket endpoints.

These tests exercise the FastAPI endpoints through HTTP requests rather
than calling the TicketService directly. Together they verify:

- Listing tickets
- Filtering by status
- Filtering by cohort
- Cursor pagination
- Limit parameter
- Viewing a ticket
- Resolving a ticket
- Validation errors
- Authentication requirements
"""

from __future__ import annotations

import asyncio
import base64

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_session
from app.main import app
from app.models.session import Session as ChatSession
from app.schemas.ticket import ConversationSummary, EscalationEvent
from app.services.ticket_service import ticket_service

TICKETS_PREFIX = "/api/v1/ops/tickets"


def _fake_session() -> ChatSession:
    """Return a fake authenticated session for endpoint tests."""
    return ChatSession(
        id="session-auth-test",
        user_id=1,
        name="Test Session",
        username="testuser",
    )


@pytest.fixture()
def client():
    """Return a TestClient with authentication overridden."""
    app.dependency_overrides[get_current_session] = _fake_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client():
    """Return a TestClient using the real authentication dependency."""
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        yield client


class TestListTickets:
    """Tests for GET /tickets."""

    def test_list_returns_created_tickets(self, client):
        """Verify listing tickets returns previously created tickets."""

        asyncio.run(
            ticket_service.create_ticket(
                EscalationEvent(
                    session_id="session-1",
                    cohort_id="cohort-a",
                ),
                ConversationSummary(
                    summary={"text": "one"},
                ),
            )
        )

        response = client.get(f"{TICKETS_PREFIX}/")

        assert response.status_code == 200

        body = response.json()

        assert isinstance(body, dict)
        assert "tickets" in body
        assert "next_cursor" in body

        tickets = body["tickets"]

        assert isinstance(tickets, list)
        assert len(tickets) == 1

        ticket = next(
            t for t in tickets
            if t["session_id"] == "session-1"
        )

        assert ticket["cohort_id"] == "cohort-a"
        assert ticket["status"] == "OPEN"
        assert ticket["summary"] == {"text": "one"}

    def test_list_filters_by_status(self, client):
        """Verify filtering tickets by status."""

        ticket = asyncio.run(
            ticket_service.create_ticket(
                EscalationEvent(
                    session_id="session-2",
                    cohort_id="cohort-a",
                ),
                ConversationSummary(
                    summary={"text": "one"},
                ),
            )
        )

        asyncio.run(
            ticket_service.resolve_ticket(
                ticket.id,
                "Resolved",
            )
        )

        response = client.get(
            f"{TICKETS_PREFIX}/",
            params={"status": "RESOLVED"},
        )

        assert response.status_code == 200

        body = response.json()
        tickets = body["tickets"]

        assert len(tickets) >= 1
        assert all(
        ticket["status"] == "RESOLVED"
        for ticket in tickets
        )

    def test_list_filters_by_cohort(self, client):
        """Verify filtering tickets by cohort."""

        asyncio.run(
            ticket_service.create_ticket(
                EscalationEvent(
                    session_id="session-3",
                    cohort_id="cohort-special",
                ),
                ConversationSummary(
                    summary={"text": "one"},
                ),
            )
        )

        response = client.get(
            f"{TICKETS_PREFIX}/",
            params={"cohort_id": "cohort-special"},
        )

        assert response.status_code == 200

        body = response.json()
        tickets = body["tickets"]

        assert len(tickets) >= 1
        assert all(
            ticket["cohort_id"] == "cohort-special"
            for ticket in tickets
        )

    def test_list_respects_limit(self, client):
        """Verify the limit parameter restricts returned tickets."""

        for i in range(5):
            asyncio.run(
                ticket_service.create_ticket(
                    EscalationEvent(
                        session_id=f"session-{i}",
                        cohort_id="cohort-a",
                    ),
                    ConversationSummary(
                        summary={"text": str(i)},
                    ),
                )
            )

        response = client.get(
            f"{TICKETS_PREFIX}/",
            params={"limit": 3},
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body["tickets"]) == 3

    def test_list_cursor_pagination(self, client):
        """Verify cursor pagination returns tickets after the cursor."""

        created = []

        for i in range(3):
            ticket = asyncio.run(
                ticket_service.create_ticket(
                    EscalationEvent(
                        session_id=f"session-{i}",
                        cohort_id="cohort-a",
                    ),
                    ConversationSummary(
                        summary={"text": str(i)},
                    ),
                )
            )
            created.append(ticket)

        cursor = base64.b64encode(
            f"{created[0].created_at.isoformat()}|{created[0].id}".encode()
        ).decode()

        response = client.get(
            f"{TICKETS_PREFIX}/",
            params={"cursor": cursor},
        )

        assert response.status_code == 200

        body = response.json()
        tickets = body["tickets"]

        assert len(tickets) == 2
        assert all(
            ticket["id"] != created[0].id
            for ticket in tickets
        )

    def test_invalid_status_returns_422(self, client):
        """Verify invalid status values fail validation."""

        response = client.get(
            f"{TICKETS_PREFIX}/",
            params={"status": "INVALID"},
        )

        assert response.status_code == 422


class TestViewTicket:
    """Tests for GET /tickets/{ticket_id}."""

    def test_view_existing_ticket_returns_200(self, client):
        """Verify an existing ticket can be retrieved."""

        created = asyncio.run(
            ticket_service.create_ticket(
                EscalationEvent(
                    session_id="session-1",
                    cohort_id="cohort-a",
                ),
                ConversationSummary(
                    summary={"text": "hello"},
                ),
            )
        )

        response = client.get(
            f"{TICKETS_PREFIX}/{created.id}"
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == created.id
        assert body["session_id"] == "session-1"
        assert body["status"] == "OPEN"
        assert body["summary"] == {"text": "hello"}

    def test_view_missing_ticket_returns_404(self, client):
        """Verify requesting an unknown ticket returns 404."""

        response = client.get(
            f"{TICKETS_PREFIX}/does-not-exist"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Ticket not found"


class TestResolveTicket:
    """Tests for POST /tickets/{ticket_id}/resolve."""

    def test_resolve_open_ticket_returns_200(self, client):
        """Verify resolving an open ticket succeeds."""

        created = asyncio.run(
            ticket_service.create_ticket(
                EscalationEvent(
                    session_id="session-1",
                    cohort_id="cohort-a",
                ),
                ConversationSummary(
                    summary={"text": "issue"},
                ),
            )
        )

        response = client.post(
            f"{TICKETS_PREFIX}/{created.id}/resolve",
            json={
                "resolution_note": "Fixed via password reset."
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["status"] == "RESOLVED"
        assert body["resolution_note"] == "Fixed via password reset."
        assert body["resolved_at"] is not None

    def test_resolving_already_resolved_ticket_returns_400(self, client):
        """Verify resolving an already resolved ticket returns 400."""

        created = asyncio.run(
            ticket_service.create_ticket(
                EscalationEvent(
                    session_id="session-2",
                    cohort_id="cohort-a",
                ),
                ConversationSummary(
                    summary={"text": "issue"},
                ),
            )
        )

        response = client.post(
            f"{TICKETS_PREFIX}/{created.id}/resolve",
            json={
                "resolution_note": "First resolution",
            },
        )

        assert response.status_code == 200

        response = client.post(
            f"{TICKETS_PREFIX}/{created.id}/resolve",
            json={
                "resolution_note": "Second resolution",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Ticket is already resolved"

    def test_resolving_missing_ticket_returns_404(self, client):
        """Verify resolving a nonexistent ticket returns 404."""

        response = client.post(
            f"{TICKETS_PREFIX}/does-not-exist/resolve",
            json={
                "resolution_note": "Anything",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Ticket not found"

    def test_resolve_without_resolution_note_returns_422(self, client):
        """Verify validation fails when resolution_note is omitted."""

        created = asyncio.run(
            ticket_service.create_ticket(
                EscalationEvent(
                    session_id="session-3",
                    cohort_id="cohort-a",
                ),
                ConversationSummary(
                    summary={"text": "issue"},
                ),
            )
        )

        response = client.post(
            f"{TICKETS_PREFIX}/{created.id}/resolve",
            json={},
        )

        assert response.status_code == 422


class TestAuthRequired:
    """Authentication tests for the ticket endpoints."""

    def test_list_without_auth_returns_401(self, unauthenticated_client):
        """Verify listing tickets requires authentication."""

        response = unauthenticated_client.get(
            f"{TICKETS_PREFIX}/"
        )

        assert response.status_code == 401

    def test_view_without_auth_returns_401(self, unauthenticated_client):
        """Verify viewing a ticket requires authentication."""

        response = unauthenticated_client.get(
            f"{TICKETS_PREFIX}/some-id"
        )

        assert response.status_code == 401

    def test_resolve_without_auth_returns_401(self, unauthenticated_client):
        """Verify resolving a ticket requires authentication."""

        response = unauthenticated_client.post(
            f"{TICKETS_PREFIX}/some-id/resolve",
            json={
                "resolution_note": "note",
            },
        )

        assert response.status_code == 401