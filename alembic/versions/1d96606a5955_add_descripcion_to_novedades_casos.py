"""add descripcion to novedades_casos

Revision ID: 1d96606a5955
Revises: d5807e0d02e1
Create Date: 2026-06-03 21:57:03.031659+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1d96606a5955'
down_revision: Union[str, None] = 'd5807e0d02e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('novedades_casos', sa.Column('descripcion', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('novedades_casos', 'descripcion')
