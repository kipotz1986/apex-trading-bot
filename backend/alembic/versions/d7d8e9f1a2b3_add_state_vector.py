"""add_state_vector_to_logs

Revision ID: d7d8e9f1a2b3
Revises: c08fce7a55e1
Create Date: 2026-05-10 13:40:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7d8e9f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'c08fce7a55e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add state_vector to decision_logs
    op.add_column('decision_logs', sa.Column('state_vector', sa.JSON(), nullable=True))
    
def downgrade() -> None:
    op.drop_column('decision_logs', 'state_vector')
