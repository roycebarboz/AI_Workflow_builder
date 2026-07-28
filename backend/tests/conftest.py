import os

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    """A TestClient backed by a fresh SQLite in-memory DB per test.

    Per the spec's testing decisions: the single HTTP seam (TestClient)
    covers CRUD and orchestration alike; only the OpenAI client is
    stubbed elsewhere. SQLite in-memory stands in for Postgres here for
    speed — schema is identical since no Postgres-only types are used.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
