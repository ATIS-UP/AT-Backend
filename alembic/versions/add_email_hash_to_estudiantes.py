"""add email_hash column to estudiantes

Revision ID: add_email_hash_to_estudiantes
Revises: add_sede_to_estudiantes
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_email_hash_to_estudiantes'
down_revision: Union[str, None] = 'add_sede_to_estudiantes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('estudiantes', sa.Column('email_hash', sa.String(64), nullable=True, unique=True, index=True))


def downgrade() -> None:
    op.drop_column('estudiantes', 'email_hash')
