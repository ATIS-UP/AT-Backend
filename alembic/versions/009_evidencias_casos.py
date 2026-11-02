
"""Crear tabla de evidencias fotográficas de casos especiales."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "009_evidencias_casos"
down_revision = "20260624_180000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidencias_casos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "registro_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "registros_casos_especiales.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "nombre",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "ruta",
            sa.String(500),
            nullable=False,
        ),
        sa.Column(
            "tipo",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_evidencias_casos_registro_id",
        "evidencias_casos",
        ["registro_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidencias_casos_registro_id",
        table_name="evidencias_casos",
    )
    op.drop_table("evidencias_casos")
