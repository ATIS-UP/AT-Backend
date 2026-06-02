"""add descripcion to novedades_casos

Revision ID: 008_add_descripcion_novedades
Revises: 007
Create Date: 2026-06-01 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "008_add_descripcion_novedades"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "novedades_casos",
        sa.Column("descripcion", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("novedades_casos", "descripcion")
