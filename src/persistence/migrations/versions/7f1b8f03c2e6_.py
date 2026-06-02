"""empty message

Revision ID: 7f1b8f03c2e6
Revises: 
Create Date: 2026-06-02 21:46:01.551593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f1b8f03c2e6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'phone_number')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('users', sa.Column('phone_number', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('first_name', sa.String(length=100), nullable=False))
