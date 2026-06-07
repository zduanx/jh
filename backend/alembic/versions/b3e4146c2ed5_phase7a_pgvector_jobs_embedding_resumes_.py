"""phase7a_pgvector_jobs_embedding_resumes_table

Revision ID: b3e4146c2ed5
Revises: 951da046d96d
Create Date: 2026-06-06 20:11:43.380687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'b3e4146c2ed5'
down_revision: Union[str, Sequence[str], None] = '951da046d96d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Voyage voyage-3 embedding dimension (ADR-032). Must match models.job.EMBEDDING_DIM.
EMBEDDING_DIM = 1024


def upgrade() -> None:
    """Phase 7A: enable pgvector, add jobs.embedding + HNSW index, create resumes table."""
    # pgvector extension (must exist before any vector column).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # jobs.embedding — semantic vector for RAG job matching (nullable until embedded).
    op.add_column("jobs", sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True))
    # HNSW index for fast cosine ANN search.
    op.execute(
        "CREATE INDEX idx_jobs_embedding_hnsw ON jobs "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # resumes — profile-level resume per user (ADR-032 / Phase 7A).
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.BigInteger(),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("s3_url", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", name="uq_resumes_user_id"),
    )


def downgrade() -> None:
    """Reverse Phase 7A schema changes."""
    op.drop_table("resumes")
    op.execute("DROP INDEX IF EXISTS idx_jobs_embedding_hnsw")
    op.drop_column("jobs", "embedding")
    # Leave the `vector` extension in place (harmless; other objects may rely on it).
