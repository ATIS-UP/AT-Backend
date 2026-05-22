"""add_cascade_delete_on_estudiante_fks

Revision ID: 0a7c87dd0137
Revises: 003
Create Date: 2026-05-22 18:17:21.792453+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a7c87dd0137'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('alertas_estudiante_id_fkey', 'alertas', type_='foreignkey')
    op.create_foreign_key('alertas_estudiante_id_fkey', 'alertas', 'estudiantes', ['estudiante_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('inscripciones_estudiante_id_fkey', 'inscripciones', type_='foreignkey')
    op.create_foreign_key('inscripciones_estudiante_id_fkey', 'inscripciones', 'estudiantes', ['estudiante_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('respuestas_encuestas_estudiante_id_fkey', 'respuestas_encuestas', type_='foreignkey')
    op.create_foreign_key('respuestas_encuestas_estudiante_id_fkey', 'respuestas_encuestas', 'estudiantes', ['estudiante_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('artefactos_estudiante_id_fkey', 'artefactos', type_='foreignkey')
    op.create_foreign_key('artefactos_estudiante_id_fkey', 'artefactos', 'estudiantes', ['estudiante_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('registros_casos_especiales_estudiante_id_fkey', 'registros_casos_especiales', type_='foreignkey')
    op.create_foreign_key('registros_casos_especiales_estudiante_id_fkey', 'registros_casos_especiales', 'estudiantes', ['estudiante_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('registros_casos_especiales_estudiante_id_fkey', 'registros_casos_especiales', type_='foreignkey')
    op.create_foreign_key('registros_casos_especiales_estudiante_id_fkey', 'registros_casos_especiales', 'estudiantes', ['estudiante_id'], ['id'])

    op.drop_constraint('artefactos_estudiante_id_fkey', 'artefactos', type_='foreignkey')
    op.create_foreign_key('artefactos_estudiante_id_fkey', 'artefactos', 'estudiantes', ['estudiante_id'], ['id'])

    op.drop_constraint('respuestas_encuestas_estudiante_id_fkey', 'respuestas_encuestas', type_='foreignkey')
    op.create_foreign_key('respuestas_encuestas_estudiante_id_fkey', 'respuestas_encuestas', 'estudiantes', ['estudiante_id'], ['id'])

    op.drop_constraint('inscripciones_estudiante_id_fkey', 'inscripciones', type_='foreignkey')
    op.create_foreign_key('inscripciones_estudiante_id_fkey', 'inscripciones', 'estudiantes', ['estudiante_id'], ['id'])

    op.drop_constraint('alertas_estudiante_id_fkey', 'alertas', type_='foreignkey')
    op.create_foreign_key('alertas_estudiante_id_fkey', 'alertas', 'estudiantes', ['estudiante_id'], ['id'])
