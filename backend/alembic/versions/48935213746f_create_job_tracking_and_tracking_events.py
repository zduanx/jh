"""create_job_tracking_and_tracking_events

Revision ID: 48935213746f
Revises: 6147d489fb1a
Create Date: 2026-01-21 23:35:59.328586

Phase 4A: Job tracking database schema (ADR-023)
- job_tracking: Stores tracking metadata (stage, notes, resume)
- tracking_events: Stores individual events for calendar queries
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '48935213746f'
down_revision: Union[str, Sequence[str], None] = '6147d489fb1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the enum values
tracking_stage_enum = postgresql.ENUM(
    'interested', 'applied', 'screening', 'interviewing',
    'offer', 'accepted', 'rejected',
    name='tracking_stage',
    create_type=False  # We'll create it explicitly
)


def upgrade() -> None:
    """Create job_tracking and tracking_events tables."""
    # Create the enum type first
    tracking_stage_enum.create(op.get_bind(), checkfirst=True)

    # Create job_tracking table
    op.create_table('job_tracking',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('stage', tracking_stage_enum, nullable=False, server_default='interested'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('resume_s3_url', sa.Text(), nullable=True),
        sa.Column('tracked_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'job_id', name='uq_user_job_tracking')
    )

    # Indexes for job_tracking
    op.create_index('idx_job_tracking_user_id', 'job_tracking', ['user_id'])
    op.create_index('idx_job_tracking_job_id', 'job_tracking', ['job_id'])

    # Create tracking_events table
    op.create_table('tracking_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tracking_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('event_time', sa.Time(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tracking_id'], ['job_tracking.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for tracking_events (date index critical for calendar queries)
    op.create_index('idx_tracking_events_tracking_id', 'tracking_events', ['tracking_id'])
    op.create_index('idx_tracking_events_date', 'tracking_events', ['event_date'])


def downgrade() -> None:
    """Drop job_tracking and tracking_events tables."""
    op.drop_index('idx_tracking_events_date', table_name='tracking_events')
    op.drop_index('idx_tracking_events_tracking_id', table_name='tracking_events')
    op.drop_table('tracking_events')

    op.drop_index('idx_job_tracking_job_id', table_name='job_tracking')
    op.drop_index('idx_job_tracking_user_id', table_name='job_tracking')
    op.drop_table('job_tracking')

    # Drop the enum type
    tracking_stage_enum.drop(op.get_bind(), checkfirst=True)
