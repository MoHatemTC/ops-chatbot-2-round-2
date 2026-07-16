"""Tests for Sprint 1 Chat Session."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import router
from app.graph.state import GraphState


def create_test_app():
    """Create a temporary FastAPI app for router testing."""
    app = FastAPI()
    app.include_router(router)
    return app


def test_graph_state_has_required_fields():
    """Graph state should carry required Sprint 1 context."""
    state = GraphState(
        session_id="session-1",
        user_id="user-1",
        username="ashraf",
        cohort="round-2",
    )

    assert state.session_id == "session-1"
    assert state.user_id == "user-1"
    assert state.username == "ashraf"
    assert state.cohort == "round-2"


def test_graph_state_default_memory():
    """Conversation memory should default to empty."""
    state = GraphState(
        session_id="session-1",
        user_id="user-1",
        username="ashraf",
    )

    assert state.messages == []
    assert state.long_term_memory == ""
    assert state.cohort is None


def test_chat_endpoint_requires_authentication():
    """JWT authentication should be enforced."""
    app = create_test_app()
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ]
        },
    )

    assert response.status_code in (401, 403)


def test_stream_endpoint_requires_authentication():
    """Streaming endpoint should reject anonymous users."""
    app = create_test_app()
    client = TestClient(app)

    response = client.post(
        "/chat/stream",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ]
        },
    )

    assert response.status_code in (401, 403)
