"""add run_metadata and raw_s3_url for Phase 2J

Revision ID: b3c7d8e9f0a1
Revises: a2ef3e15d65e
Create Date: 2026-01-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'b3c7d8e9f0a1'
down_revision: Union[str, Sequence[str], None] = 'a2ef3e15d65e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add run_metadata to ingestion_runs and raw_s3_url to jobs for Phase 2J."""

    # Add run_metadata JSONB column to ingestion_runs
    # Note: "metadata" is reserved in SQLAlchemy, so we use "run_metadata"
    # Stores per-company failure counts: {"google_failures": 0, "amazon_failures": 2, ...}
    op.add_column(
        'ingestion_runs',
        sa.Column('run_metadata', JSONB, server_default='{}', nullable=False)
    )

    # Add raw_s3_url to jobs
    # Stores S3 path: s3://bucket/raw/{company}/{external_id}.html
    op.add_column(
        'jobs',
        sa.Column('raw_s3_url', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove run_metadata and raw_s3_url columns."""
    op.drop_column('jobs', 'raw_s3_url')
    op.drop_column('ingestion_runs', 'run_metadata')
