"""add_paused_until_to_risk_state

Revision ID: e1f2g3h4i5j6
Revises: d7d8e9f1a2b3
Create Date: 2026-05-11 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, Sequence[str], None] = 'd7d8e9f1a2b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('risk_state', sa.Column('paused_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('risk_state', 'paused_until')
