"""add ingreso_familiar to estudiantes

Revision ID: fe063202f87b
Revises: 008_add_descripcion_novedades
Create Date: 2026-06-03 18:18:18.359080+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe063202f87b'
down_revision: Union[str, None] = '008_add_descripcion_novedades'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('estudiantes', sa.Column('ingreso_familiar', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('estudiantes', 'ingreso_familiar')
