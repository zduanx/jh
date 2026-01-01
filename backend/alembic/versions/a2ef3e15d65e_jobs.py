"""jobs

Revision ID: a2ef3e15d65e
Revises: 87f2af0cf6df
Create Date: 2025-12-31 17:19:12.222185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a2ef3e15d65e'
down_revision: Union[str, Sequence[str], None] = '87f2af0cf6df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ingestion_runs and jobs tables for Phase 2F."""

    # Create ingestion_runs table
    op.create_table(
        'ingestion_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        # status: pending, initializing, ingesting, finished, error
        sa.Column('total_jobs', sa.Integer(), server_default='0', nullable=False),
        # Snapshot fields (written on completion)
        sa.Column('jobs_ready', sa.Integer(), nullable=True),
        sa.Column('jobs_skipped', sa.Integer(), nullable=True),
        sa.Column('jobs_expired', sa.Integer(), nullable=True),
        sa.Column('jobs_failed', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('finished_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('company', sa.String(length=100), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        # status: pending, ready, skipped, expired, error
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('simhash', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['ingestion_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'company', 'external_id', name='uq_user_company_job')
    )

    # Create index for SSE progress query (WHERE run_id = ? GROUP BY status)
    # Note: idx_jobs_user_company is NOT needed - UNIQUE(user_id, company, external_id) covers it via prefix matching
    op.create_index('idx_jobs_run_status', 'jobs', ['run_id', 'status'])


def downgrade() -> None:
    """Drop ingestion_runs and jobs tables."""
    op.drop_index('idx_jobs_run_status', table_name='jobs')
    op.drop_table('jobs')
    op.drop_table('ingestion_runs')
