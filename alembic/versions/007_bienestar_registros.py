"""create bienestar_registros table

Revision ID: 007
Revises: 006
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bienestar_registros",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("periodo", sa.String(20), nullable=False, index=True),
        sa.Column("servicio", sa.String(50), nullable=False, index=True),
        sa.Column("cantidad", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("periodo", "servicio", name="uq_bienestar_periodo_servicio"),
    )


def downgrade() -> None:
    op.drop_table("bienestar_registros")
