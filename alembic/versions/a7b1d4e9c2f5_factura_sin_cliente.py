"""facturas.sin_cliente: ingresos sin factura a un cliente

Revision ID: a7b1d4e9c2f5
Revises: f6a0c3d8e1b4
Create Date: 2026-10-10 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b1d4e9c2f5'
down_revision: Union[str, None] = 'f6a0c3d8e1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('facturas') as batch:
        batch.add_column(sa.Column('sin_cliente', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('facturas') as batch:
        batch.drop_column('sin_cliente')
