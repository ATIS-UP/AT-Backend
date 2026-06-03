"""add CASCADE to historial_registros.registro_id FK

Revision ID: a378c4c546e4
Revises: 1d96606a5955
Create Date: 2026-06-03 22:25:05.566916+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a378c4c546e4'
down_revision: Union[str, None] = '1d96606a5955'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('historial_registros_registro_id_fkey', 'historial_registros', type_='foreignkey')
    op.create_foreign_key(
        'historial_registros_registro_id_fkey', 'historial_registros',
        'registros_casos_especiales', ['registro_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('historial_registros_registro_id_fkey', 'historial_registros', type_='foreignkey')
    op.create_foreign_key(
        'historial_registros_registro_id_fkey', 'historial_registros',
        'registros_casos_especiales', ['registro_id'], ['id']
    )
