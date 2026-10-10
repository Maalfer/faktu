"""conceptos por trimestre

Revision ID: b7f1c2a9d4e0
Revises: 36ec3cadc755
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f1c2a9d4e0'
down_revision: Union[str, None] = '36ec3cadc755'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conceptos_trimestre',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('trimestre', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=10), nullable=False),
        sa.Column('concepto', sa.String(length=300), nullable=False),
        sa.Column('importe', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('iva', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('orden', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_conceptos_trimestre_user_id'), 'conceptos_trimestre', ['user_id'], unique=False)
    op.create_index(op.f('ix_conceptos_trimestre_year'), 'conceptos_trimestre', ['year'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_conceptos_trimestre_year'), table_name='conceptos_trimestre')
    op.drop_index(op.f('ix_conceptos_trimestre_user_id'), table_name='conceptos_trimestre')
    op.drop_table('conceptos_trimestre')
