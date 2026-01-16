"""add_search_indexes

Revision ID: 6147d489fb1a
Revises: b3c7d8e9f0a1
Create Date: 2026-01-15

Phase 3C: Add full-text search (tsvector) and fuzzy search (pg_trgm) indexes.

Search strategy (per ADR-014):
- tsvector: Fast word matching on title + description, with stemming and ranking
- pg_trgm: Typo tolerance on title only (trigram similarity)

Query pattern:
    WHERE search_vector @@ plainto_tsquery('english', :query)  -- Full-text
       OR similarity(title, :query) > 0.2                      -- Fuzzy title
    ORDER BY ts_rank(search_vector, plainto_tsquery('english', :query)) DESC
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6147d489fb1a'
down_revision: Union[str, Sequence[str], None] = 'b3c7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add search_vector column, tsvector index, and pg_trgm index."""

    # 1. Enable pg_trgm extension (built into Neon)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. Add search_vector column for full-text search
    op.add_column('jobs', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR, nullable=True))

    # 3. Populate search_vector for existing rows
    # Weight A = title (highest priority), Weight B = description
    op.execute("""
        UPDATE jobs SET search_vector =
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
    """)

    # 4. Create GIN index on search_vector for fast full-text search
    op.execute("""
        CREATE INDEX idx_jobs_search_vector
        ON jobs USING GIN (search_vector)
    """)

    # 5. Create GIN index on title for fuzzy search (pg_trgm)
    op.execute("""
        CREATE INDEX idx_jobs_title_trgm
        ON jobs USING GIN (title gin_trgm_ops)
    """)

    # 6. Create trigger to auto-update search_vector on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION jobs_search_vector_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER jobs_search_vector_update
        BEFORE INSERT OR UPDATE OF title, description ON jobs
        FOR EACH ROW EXECUTE FUNCTION jobs_search_vector_trigger();
    """)


def downgrade() -> None:
    """Remove search indexes and search_vector column."""

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS jobs_search_vector_update ON jobs")
    op.execute("DROP FUNCTION IF EXISTS jobs_search_vector_trigger()")

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_jobs_title_trgm")
    op.execute("DROP INDEX IF EXISTS idx_jobs_search_vector")

    # Drop column
    op.drop_column('jobs', 'search_vector')

    # Note: We don't drop pg_trgm extension as other things might use it
