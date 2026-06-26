"""
Pytest fixtures for the MCP server tests (Phase 7B).

Strategy (industry-standard layering — see PHASE_7B and ADR-030):
  - Tool LOGIC is tested against the real test database (same Neon test DB and
    Alembic-migrated schema as the db service tests), so the SQL / pgvector path
    is exercised for real — only the live Voyage embedding call is faked.
  - Tools open their OWN `SessionLocal()` (they are not handed a session). To make
    those tool-opened sessions (a) see the test data and (b) roll back after each
    test, we bind `SessionLocal` to the SAME connection/transaction the test uses
    (the standard SQLAlchemy "join an external transaction" test pattern), then
    patch `mcp_server.server.SessionLocal` to that bound factory.
  - `vectorize_text` is faked with a deterministic, dependency-free embedding so
    tests are offline, free, and repeatable (no Voyage API call). ADR-032's choice
    of a cloud embedding is an integration concern, not a unit-test concern.

We reuse the db tests' `test_engine` fixture by importing their conftest as a
plugin, so the schema/migration setup lives in exactly one place.
"""
import hashlib

import pytest
from sqlalchemy.orm import sessionmaker

import mcp_server.server as server
from db.__tests__.db_test_utils import get_or_create_fixed_test_user

# Reuse the db test suite's session-scoped engine + Alembic migration bootstrap by
# IMPORTING the fixture directly (the standard cross-suite fixture-sharing pattern).
# (`pytest_plugins` can't be used in a nested conftest, and registering it top-level
# double-registers the auto-discovered db conftest — so we import the fixture instead.)
from db.__tests__.conftest import test_engine  # noqa: F401  (re-exported as a fixture)

EMBEDDING_DIM = 1024


@pytest.fixture
def anyio_backend():
    """Pin async tests (test_protocol.py) to asyncio (trio isn't installed)."""
    return "asyncio"


def fake_embedding(text: str) -> list[float]:
    """
    Deterministic 1024-dim unit-ish vector derived from the text's hash.

    Same text -> same vector (so similarity is stable across runs); different
    text -> different vector. Not semantically meaningful — we are testing the
    plumbing (query -> vector -> pgvector search -> shaped result), not retrieval
    quality (that's the eval harness's job, not a unit test).
    """
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    # Expand the 32-byte digest to 1024 floats in [-1, 1], deterministically.
    vals = []
    i = 0
    while len(vals) < EMBEDDING_DIM:
        b = seed[i % len(seed)]
        # mix in the position so the pattern doesn't just repeat every 32 dims
        mixed = (b ^ (i * 37 + 11)) & 0xFF
        vals.append((mixed / 127.5) - 1.0)
        i += 1
    return vals


@pytest.fixture
def mcp_db(test_engine, monkeypatch):
    """
    Bind the server's `SessionLocal` to a rolled-back test transaction.

    Yields a session usable for seeding fixtures (jobs, resumes). Any session the
    TOOLS open via `SessionLocal()` shares the same connection, so they see seeded
    data; everything is rolled back when the test ends.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    BoundSession = sessionmaker(bind=connection)
    # Tools call `mcp_server.server.SessionLocal()` directly — point it here.
    monkeypatch.setattr(server, "SessionLocal", BoundSession)

    seed_session = BoundSession()
    try:
        yield seed_session
    finally:
        seed_session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def fake_voyage(monkeypatch):
    """Replace the live Voyage embedding call with the deterministic fake."""
    monkeypatch.setattr(server, "vectorize_text", lambda text, input_type="document": fake_embedding(text))
    return fake_embedding


@pytest.fixture
def seed_user(mcp_db):
    """The fixed test user (reused from the db test utils)."""
    return get_or_create_fixed_test_user(mcp_db)
