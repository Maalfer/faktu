"""nombre del adjunto de gastos y notas/origen de conceptos

Revision ID: d4e8a1b6c9f2
Revises: c1a4c7d3f812
Create Date: 2026-10-10 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e8a1b6c9f2'
down_revision: Union[str, None] = 'c1a4c7d3f812'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('gastos') as batch:
        batch.add_column(sa.Column('archivo_nombre', sa.String(length=255), nullable=True))
    with op.batch_alter_table('conceptos_trimestre') as batch:
        batch.add_column(sa.Column('notas', sa.String(length=500), nullable=False, server_default=''))
        batch.add_column(sa.Column('factura_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('gasto_id', sa.Integer(), nullable=True))
        batch.create_index('ix_conceptos_trimestre_factura_id', ['factura_id'])
        batch.create_index('ix_conceptos_trimestre_gasto_id', ['gasto_id'])


def downgrade() -> None:
    with op.batch_alter_table('conceptos_trimestre') as batch:
        batch.drop_index('ix_conceptos_trimestre_gasto_id')
        batch.drop_index('ix_conceptos_trimestre_factura_id')
        batch.drop_column('gasto_id')
        batch.drop_column('factura_id')
        batch.drop_column('notas')
    with op.batch_alter_table('gastos') as batch:
        batch.drop_column('archivo_nombre')
