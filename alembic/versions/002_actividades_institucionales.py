"""actividades institucionales table

Revision ID: 002
Revises: 001
Create Date: 2026-05-14 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create enum types if they don't exist
    op.execute("DO $$ BEGIN CREATE TYPE tipoactividadinstitucional AS ENUM ('CLASE', 'REFUERZO', 'TORNEO', 'TALLER', 'SEMINARIO', 'TUTORIA', 'OTRO'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE estadoactividadinstitucional AS ENUM ('CREADA', 'EN_CURSO', 'FINALIZADA', 'CANCELADA'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE modalidadactividad AS ENUM ('PRESENCIAL', 'VIRTUAL', 'HIBRIDA'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    op.create_table(
        "actividades_institucionales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tipo",
            sa.Enum(
                "CLASE", "REFUERZO", "TORNEO", "TALLER", "SEMINARIO", "TUTORIA", "OTRO",
                name="tipoactividadinstitucional"
            ),
            nullable=False,
        ),
        sa.Column("fecha_inicio", sa.DateTime, nullable=False),
        sa.Column("fecha_fin", sa.DateTime, nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "CREADA", "EN_CURSO", "FINALIZADA", "CANCELADA",
                name="estadoactividadinstitucional"

            ),
            nullable=False,
            server_default="CREADA",
        ),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("encargado", sa.String(255), nullable=False),
        sa.Column("observaciones", sa.Text, nullable=True),
        sa.Column("anexos", sa.Text, nullable=True),
        sa.Column(
            "creador_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "modalidad",
            sa.Enum(
                "PRESENCIAL", "VIRTUAL", "HIBRIDA",
                name="modalidadactividad",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("lugar_enlace", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("actividades_institucionales")
    op.execute("DROP TYPE IF EXISTS tipoactividadinstitucional")
    op.execute("DROP TYPE IF EXISTS estadoactividadinstitucional")
    op.execute("DROP TYPE IF EXISTS modalidadactividad")
