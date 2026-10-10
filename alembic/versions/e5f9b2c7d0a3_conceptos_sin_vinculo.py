"""el libro se calcula solo: se quitan los vínculos factura_id/gasto_id de conceptos

Revision ID: e5f9b2c7d0a3
Revises: d4e8a1b6c9f2
Create Date: 2026-10-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f9b2c7d0a3'
down_revision: Union[str, None] = 'd4e8a1b6c9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('conceptos_trimestre') as batch:
        batch.drop_index('ix_conceptos_trimestre_gasto_id')
        batch.drop_index('ix_conceptos_trimestre_factura_id')
        batch.drop_column('gasto_id')
        batch.drop_column('factura_id')


def downgrade() -> None:
    with op.batch_alter_table('conceptos_trimestre') as batch:
        batch.add_column(sa.Column('factura_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('gasto_id', sa.Integer(), nullable=True))
        batch.create_index('ix_conceptos_trimestre_factura_id', ['factura_id'])
        batch.create_index('ix_conceptos_trimestre_gasto_id', ['gasto_id'])
