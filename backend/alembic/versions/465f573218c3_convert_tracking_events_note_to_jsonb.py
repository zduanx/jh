"""convert_tracking_events_note_to_jsonb

Revision ID: 465f573218c3
Revises: f5c246f90db1
Create Date: 2026-01-28

Convert tracking_events.note from TEXT to JSONB to store stage-specific data
directly on the event (e.g., {type: "phone", with_person: "xxx", note: "..."}).

This simplifies the data model by storing stage data on the event itself
rather than in job_tracking.notes.stages[event_type].
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '465f573218c3'
down_revision: Union[str, Sequence[str], None] = 'f5c246f90db1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert note column from TEXT to JSONB."""
    # Convert existing text notes to JSONB format
    # If note has text, wrap it as {"note": "..."}
    # If note is null/empty, set to empty object
    op.execute("""
        UPDATE tracking_events
        SET note = CASE
            WHEN note IS NULL THEN NULL
            WHEN note = '' THEN NULL
            ELSE jsonb_build_object('note', note)
        END
    """)

    # Alter column type to JSONB
    op.alter_column(
        'tracking_events',
        'note',
        type_=JSONB,
        postgresql_using='note::jsonb',
        nullable=True
    )


def downgrade() -> None:
    """Convert note column back to TEXT."""
    # Extract 'note' field from JSONB back to text
    op.execute("""
        UPDATE tracking_events
        SET note = note->>'note'
    """)

    # Alter column type back to TEXT
    op.alter_column(
        'tracking_events',
        'note',
        type_=sa.Text,
        postgresql_using='note::text',
        nullable=True
    )
