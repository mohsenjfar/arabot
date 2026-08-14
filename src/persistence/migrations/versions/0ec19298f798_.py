"""widen resources.user_id to bigint

Revision ID: 0ec19298f798
Revises: ba1771db5274
Create Date: 2026-08-13 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ec19298f798'
down_revision: Union[str, Sequence[str], None] = 'ba1771db5274'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Telegram user ids exceed 32-bit int range (matches users.id/tasks.user_id,
    # which are already bigint in production despite the model saying Integer).
    op.alter_column('resources', 'user_id', type_=sa.BigInteger())


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('resources', 'user_id', type_=sa.Integer())
