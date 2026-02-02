"""create_stories_table

Revision ID: 951da046d96d
Revises: 465f573218c3
Create Date: 2026-02-01 23:51:43.087636

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '951da046d96d'
down_revision: Union[str, Sequence[str], None] = '465f573218c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create stories table for behavioral interview prep."""
    op.create_table('stories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('type', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=True),
        sa.Column('situation', sa.Text(), nullable=True),
        sa.Column('task', sa.Text(), nullable=True),
        sa.Column('action', sa.Text(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stories_user_id', 'stories', ['user_id'], unique=False)
    op.create_index('idx_stories_type', 'stories', ['type'], unique=False)
    op.create_index('idx_stories_tags', 'stories', ['tags'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    """Drop stories table."""
    op.drop_index('idx_stories_tags', table_name='stories', postgresql_using='gin')
    op.drop_index('idx_stories_type', table_name='stories')
    op.drop_index('idx_stories_user_id', table_name='stories')
    op.drop_table('stories')
