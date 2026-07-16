"""State schema for the Sprint 1 Chat Session LangGraph."""

from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class GraphState(BaseModel):
    """Checkpointed state shared across conversational turns."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list,
        description="Conversation messages.",
    )

    long_term_memory: str = Field(
        default="",
        description="Retrieved long-term memory for the current conversation.",
    )

    session_id: str = Field(
        description="Unique chat session identifier.",
    )

    user_id: str = Field(
        description="Authenticated user identifier.",
    )

    username: str = Field(
        description="Authenticated user's display name.",
    )

    cohort: str | None = Field(
        default=None,
        description="User cohort context carried across turns.",
    )

