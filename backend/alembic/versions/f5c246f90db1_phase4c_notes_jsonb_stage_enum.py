"""phase4c_notes_jsonb_stage_enum

Revision ID: f5c246f90db1
Revises: 48935213746f
Create Date: 2026-01-23 01:57:06.732055

Phase 4C changes:
1. Convert notes column from TEXT to JSONB for structured stage data
2. Update tracking_stage enum:
   - Keep: interested (initial save/bookmark stage)
   - Rename: interviewing -> interview
   - Add: reference, declined
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f5c246f90db1'
down_revision: Union[str, Sequence[str], None] = '48935213746f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Convert notes column from TEXT to JSONB
    # First, convert existing text notes to JSONB format
    op.execute("""
        UPDATE job_tracking
        SET notes = CASE
            WHEN notes IS NULL THEN '{}'::jsonb
            WHEN notes = '' THEN '{}'::jsonb
            ELSE jsonb_build_object('legacy_note', notes)
        END
    """)

    # Alter column type to JSONB
    op.alter_column(
        'job_tracking',
        'notes',
        type_=JSONB,
        postgresql_using='notes::jsonb',
        nullable=True
    )

    # Set default for new rows
    op.alter_column(
        'job_tracking',
        'notes',
        server_default=sa.text("'{}'::jsonb")
    )

    # 2. Update tracking_stage enum
    # Add new values - must commit before using them (PostgreSQL requirement)
    op.execute("ALTER TYPE tracking_stage ADD VALUE IF NOT EXISTS 'interview'")
    op.execute("ALTER TYPE tracking_stage ADD VALUE IF NOT EXISTS 'reference'")
    op.execute("ALTER TYPE tracking_stage ADD VALUE IF NOT EXISTS 'declined'")
    op.execute("COMMIT")

    # Migrate existing data: interviewing -> interview (renamed)
    op.execute("UPDATE job_tracking SET stage = 'interview' WHERE stage = 'interviewing'")

    # 3. Create event_type enum and convert tracking_events.event_type column
    # Event types mirror stages but exclude 'interested' (not an actionable event)
    op.execute("""
        CREATE TYPE event_type AS ENUM (
            'applied', 'screening', 'interview', 'reference',
            'offer', 'accepted', 'declined', 'rejected'
        )
    """)

    # Convert event_type column from varchar to enum
    # First handle any 'interviewing' values
    op.execute("UPDATE tracking_events SET event_type = 'interview' WHERE event_type = 'interviewing'")

    op.alter_column(
        'tracking_events',
        'event_type',
        type_=sa.Enum(
            'applied', 'screening', 'interview', 'reference',
            'offer', 'accepted', 'declined', 'rejected',
            name='event_type'
        ),
        postgresql_using='event_type::event_type'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Enum value removal in PostgreSQL requires recreating the type
    # This is a simplified downgrade that keeps the enum values but reverts data

    # 1. Revert event_type column back to varchar
    op.alter_column(
        'tracking_events',
        'event_type',
        type_=sa.String(50),
        postgresql_using='event_type::text'
    )

    # Drop event_type enum
    op.execute("DROP TYPE IF EXISTS event_type")

    # Migrate event data back: interview -> interviewing
    op.execute("UPDATE tracking_events SET event_type = 'interviewing' WHERE event_type = 'interview'")

    # 2. Migrate stage data back: interview -> interviewing
    op.execute("UPDATE job_tracking SET stage = 'interviewing' WHERE stage = 'interview'")
    # reference/declined have no old equivalent, move to offer
    op.execute("UPDATE job_tracking SET stage = 'offer' WHERE stage IN ('reference', 'declined')")

    # 3. Convert JSONB back to TEXT (extract legacy_note if exists)
    op.execute("""
        UPDATE job_tracking
        SET notes = COALESCE(notes->>'legacy_note', notes::text)
    """)

    # Alter column type back to TEXT
    op.alter_column(
        'job_tracking',
        'notes',
        type_=sa.Text,
        postgresql_using='notes::text',
        nullable=True,
        server_default=None
    )
