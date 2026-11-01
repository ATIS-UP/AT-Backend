"""add mfa_methods column and backup_codes table

Revision ID: 20260624_180000
Revises: 20260614_203211
Create Date: 2026-06-24 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "20260624_180000"
down_revision: Union[str, None] = "20260614_203211"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_methods", sa.ARRAY(sa.String()), server_default="{}", nullable=False))
    op.create_table(
        "backup_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("backup_codes")
    op.drop_column("users", "mfa_methods")
