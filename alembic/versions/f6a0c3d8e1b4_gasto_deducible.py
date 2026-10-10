"""gastos.deducible: documentos que se conservan pero no computan

Revision ID: f6a0c3d8e1b4
Revises: e5f9b2c7d0a3
Create Date: 2026-10-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a0c3d8e1b4'
down_revision: Union[str, None] = 'e5f9b2c7d0a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('gastos') as batch:
        batch.add_column(sa.Column('deducible', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table('gastos') as batch:
        batch.drop_column('deducible')
