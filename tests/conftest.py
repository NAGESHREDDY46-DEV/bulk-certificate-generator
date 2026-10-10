# tests/conftest.py
# Shared pytest fixtures for all test modules.
#
# The key SQLite in-memory gotcha:
#   sqlite:///:memory: gives every NEW connection its own empty database.
#   SQLAlchemy's default connection pool opens separate connections, so
#   `create_all()` writes tables to connection A, but the session ends up
#   on connection B — which sees an empty database ("no such table").
#
# Fix: StaticPool
#   StaticPool makes SQLAlchemy reuse the SAME underlying sqlite3 connection
#   for every checkout. This means create_all() and all session operations
#   share one connection and therefore one in-memory database.
#
# Isolation strategy:
#   One engine (and therefore one in-memory DB) per test function.
#   Fresh engine = fresh schema = perfect isolation at minimal cost.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Side-effect imports: register Job and Certificate with Base.metadata
# so that create_all() knows which tables to create.
from app.models import job, certificate  # noqa: F401
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def test_engine():
    """
    Fresh in-memory SQLite database for one test.
    StaticPool ensures all operations share the same sqlite3 connection,
    so every table created by create_all() is visible to the session.
    """
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,   # <-- the critical fix
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    """A session bound to the test engine, closed after the test."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    """
    FastAPI TestClient wired to the in-memory test session.
    All HTTP requests within one test share the same db_session, so rows
    committed by one request are immediately visible to the next.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
