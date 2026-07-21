"""Shared pytest fixtures for ticket service tests."""

import pytest
from sqlmodel import Session, SQLModel

from app.models.user import User
from app.models.session import Session as ChatSession
from app.services.database import database_service


@pytest.fixture(autouse=True)
def test_db():
    """Prepare a clean database before each test."""

    engine = database_service.engine

    # Reset the database before every test
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Create a test user
        user = User(
            id=1,
            email="test@example.com",
            hashed_password=User.hash_password("password"),
            username="testuser",
        )
        session.add(user)

        # Create several chat sessions that ticket tests can reference
        for i in range(10):
            session.add(
                ChatSession(
                    id=f"session-{i}",
                    user_id=1,
                    name=f"Test Session {i}",
                    username="testuser",
                )
            )

        session.commit()

    yield