"""add novedad_caso table, novedad_id column, and new tipo enum values

Revision ID: 1a2b3c4d5e6f
Revises: 0a7c87dd0137
Create Date: 2026-05-22 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "0a7c87dd0137"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.engine.name == "postgresql"

    if is_pg:
        op.execute("COMMIT")
        op.execute("ALTER TYPE tiporegistrocaso ADD VALUE IF NOT EXISTS 'PSICOSOCIAL'")
        op.execute("ALTER TYPE tiporegistrocaso ADD VALUE IF NOT EXISTS 'INSTITUCIONAL_VOCACIONAL'")

    op.execute("""
        CREATE TABLE IF NOT EXISTS novedades_casos (
            id UUID PRIMARY KEY,
            tipo_caso VARCHAR(50) NOT NULL,
            nombre VARCHAR(200) NOT NULL,
            activo BOOLEAN DEFAULT true,
            orden INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT now()
        )
    """)
    if is_pg:
        op.execute("CREATE INDEX IF NOT EXISTS ix_novedades_casos_tipo_caso ON novedades_casos(tipo_caso)")

    op.execute("""
        ALTER TABLE registros_casos_especiales
        ADD COLUMN IF NOT EXISTS novedad_id UUID REFERENCES novedades_casos(id)
    """)


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.engine.name == "postgresql"

    if is_pg:
        op.execute("ALTER TABLE registros_casos_especiales DROP CONSTRAINT IF EXISTS registros_casos_especiales_novedad_id_fkey")
    op.execute("ALTER TABLE registros_casos_especiales DROP COLUMN IF EXISTS novedad_id")
    op.execute("DROP TABLE IF EXISTS novedades_casos")
