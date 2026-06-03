"""add documento_hash to estudiantes

Revision ID: d5807e0d02e1
Revises: fe063202f87b
Create Date: 2026-06-03 20:23:28.651850+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5807e0d02e1'
down_revision: Union[str, None] = 'fe063202f87b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('estudiantes', sa.Column('documento_hash', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_estudiantes_documento_hash'), 'estudiantes', ['documento_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_estudiantes_documento_hash'), table_name='estudiantes')
    op.drop_column('estudiantes', 'documento_hash')
