"""Tests for the ticket knowledge service.

Verifies that resolving an Operations ticket produces a normalized
knowledge-base Document and passes it to the ingestion pipeline, allowing
future users with similar questions to be answered automatically through
knowledge retrieval.
"""

from unittest.mock import patch

from app.models.ticket import Ticket, TicketStatus
from app.services.ticket_knowledge_service import ticket_knowledge_service


class TestTicketKnowledgeService:
    """Tests for TicketKnowledgeService."""

    @patch("app.services.ticket_knowledge_service.ingest_document")
    def test_ingest_resolved_ticket_creates_document(self, mock_ingest):
        """Verify a resolved ticket is converted into a knowledge document."""

        ticket = Ticket(
            id="ticket-1",
            session_id="session-1",
            cohort_id="cohort-a",
            status=TicketStatus.RESOLVED,
            summary={"text": "How do I reset my password?"},
            resolution_note="Click Forgot Password on the login page.",
        )

        ticket_knowledge_service.ingest_resolved_ticket(ticket)

        mock_ingest.assert_called_once()

        document = mock_ingest.call_args.args[0]

        assert document.id == "ticket:ticket-1"
        assert document.metadata.title == "Resolved Ticket ticket-1"
        assert document.metadata.source == "operations_ticket"
        assert document.metadata.cohort == "cohort-a"
        assert document.metadata.type.value == "faq"

        assert "How do I reset my password?" in document.raw_text
        assert "Click Forgot Password on the login page." in document.raw_text

    @patch("app.services.ticket_knowledge_service.ingest_document")
    def test_ingest_handles_missing_text_field(self, mock_ingest):
        """Verify non-standard summaries still produce a document."""

        ticket = Ticket(
            id="ticket-2",
            session_id="session-2",
            cohort_id="cohort-b",
            status=TicketStatus.RESOLVED,
            summary={"conversation": "User cannot login"},
            resolution_note="Reset the user's password.",
        )

        ticket_knowledge_service.ingest_resolved_ticket(ticket)

        mock_ingest.assert_called_once()

        document = mock_ingest.call_args.args[0]

        assert "conversation" in document.raw_text
        assert "Reset the user's password." in document.raw_text

    @patch("app.services.ticket_knowledge_service.ingest_document")
    def test_ingest_called_once(self, mock_ingest):
        """Verify exactly one ingestion request is made per resolved ticket."""

        ticket = Ticket(
            id="ticket-3",
            session_id="session-3",
            cohort_id="cohort-c",
            status=TicketStatus.RESOLVED,
            summary={"text": "Where is the schedule?"},
            resolution_note="The schedule is available in the student portal.",
        )

        ticket_knowledge_service.ingest_resolved_ticket(ticket)

        mock_ingest.assert_called_once()