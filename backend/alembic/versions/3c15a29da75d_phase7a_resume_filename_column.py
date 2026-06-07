"""phase7a_resume_filename_column

Revision ID: 3c15a29da75d
Revises: b3e4146c2ed5
Create Date: 2026-06-06 20:35:24.238165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c15a29da75d'
down_revision: Union[str, Sequence[str], None] = 'b3e4146c2ed5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add resumes.filename (original filename for display)."""
    op.add_column("resumes", sa.Column("filename", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "filename")
