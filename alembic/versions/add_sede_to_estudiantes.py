"""add sede column to estudiantes

Revision ID: add_sede_to_estudiantes
Revises: a378c4c546e4
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_sede_to_estudiantes'
down_revision: Union[str, None] = 'a378c4c546e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('estudiantes', sa.Column('sede', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('estudiantes', 'sede')
