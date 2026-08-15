"""add tasks.archived

Revision ID: a4c7e1f92b03
Revises: 0ec19298f798
Create Date: 2026-08-15 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4c7e1f92b03'
down_revision: Union[str, Sequence[str], None] = '0ec19298f798'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills existing rows to false so the reminder job's
    # `Task.archived == False` filter doesn't silently drop them via NULL's
    # three-valued SQL logic.
    op.add_column('tasks', sa.Column('archived', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tasks', 'archived')
