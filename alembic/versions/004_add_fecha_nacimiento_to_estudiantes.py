"""add fecha_nacimiento column to estudiantes

Revision ID: 004
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "estudiantes",
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("estudiantes", "fecha_nacimiento")
