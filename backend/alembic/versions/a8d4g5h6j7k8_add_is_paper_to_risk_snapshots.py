"""add_is_paper_to_risk_snapshots

Revision ID: a8d4g5h6j7k8
Revises: e28f8196c25a
Create Date: 2026-05-16 11:58:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a8d4g5h6j7k8'
down_revision = 'e28f8196c25a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('risk_snapshots', sa.Column('is_paper', sa.Boolean(), server_default='true', nullable=True))
    op.create_index(op.f('ix_risk_snapshots_is_paper'), 'risk_snapshots', ['is_paper'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_risk_snapshots_is_paper'), table_name='risk_snapshots')
    op.drop_column('risk_snapshots', 'is_paper')
