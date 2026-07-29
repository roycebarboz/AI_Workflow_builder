"""SQLAlchemy engine/session wiring, driven by DATABASE_URL."""

from __future__ import annotations

import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/ai_workflow_builder",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> sessionmaker[Session]:
    """A session *factory* rather than a request-scoped session, for callers
    that need to open/close their own session on a lifetime that outlives a
    single dependency-injected `db` — e.g. a streaming SSE response, whose
    generator body runs after FastAPI has already closed the request's
    `Depends(get_db)` session (dependency cleanup happens before the
    response body streams)."""
    return SessionLocal
