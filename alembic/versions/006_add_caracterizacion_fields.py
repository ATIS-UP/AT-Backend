"""add estrato, procedencia, genero to estudiantes

Revision ID: 006
Revises: 005
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("estudiantes", sa.Column("estrato", sa.Integer(), nullable=True))
    op.add_column("estudiantes", sa.Column("procedencia", sa.String(20), nullable=True))
    op.add_column("estudiantes", sa.Column("genero", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("estudiantes", "genero")
    op.drop_column("estudiantes", "procedencia")
    op.drop_column("estudiantes", "estrato")
