"""drop fecha_nacimiento from estudiantes

Revision ID: 005
Revises: 003
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("estudiantes", "fecha_nacimiento")


def downgrade() -> None:
    op.add_column(
        "estudiantes",
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
    )
