"""Knowledge-base integration for resolved Operations tickets.

Converts resolved tickets into normalized knowledge-base Documents and
ingests them through the existing F1.1 ingestion pipeline. This allows
human-resolved issues to become searchable knowledge so future users with
similar questions can be answered automatically without requiring another
Operations escalation.
"""

from app.core.logging import logger
from app.kb.store import ingest_document
from app.models.ticket import Ticket
from app.schemas.knowledge import (
    Document,
    DocumentMetadata,
    MaterialType,
)


class TicketKnowledgeService:
    """Stores resolved tickets in the knowledge base."""

    def ingest_resolved_ticket(self, ticket: Ticket) -> None:
        """Convert a resolved ticket into a knowledge-base document."""

        question = ticket.summary.get("text", str(ticket.summary))

        raw_text = (
            f"Question:\n{question}\n\n"
            f"Answer:\n{ticket.resolution_note}"
        )

        document = Document.create(
            id=f"ticket:{ticket.id}",
            raw_text=raw_text,
            metadata=DocumentMetadata(
                title=f"Resolved Ticket {ticket.id}",
                source="operations_ticket",
                type=MaterialType.FAQ,
                cohort=ticket.cohort_id,
            ),
        )

        try:
            ingest_document(document)
        except Exception as e:
            logger.exception(
                "failed_to_ingest_resolved_ticket",
                ticket_id=ticket.id,
                error=str(e),
            )


ticket_knowledge_service = TicketKnowledgeService()