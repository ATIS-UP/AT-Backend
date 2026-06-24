"""add mfa_secret, mfa_enabled to users and email_otp_codes table

Revision ID: 20260614_203211
Revises: 3de7e1d1cf0c
Create Date: 2026-06-14 20:32:11.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "20260614_203211"
down_revision: Union[str, None] = "3de7e1d1cf0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_secret", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    op.create_table(
        "email_otp_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("email_otp_codes")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "mfa_secret")
