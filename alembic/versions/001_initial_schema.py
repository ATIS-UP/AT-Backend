"""initial schema - captures all existing tables

Revision ID: 001
Revises: None
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum("ADMINISTRADOR", "DOCENTE", "APOYO", name="rolenum"),
            nullable=False,
            server_default="DOCENTE",
        ),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("last_login", sa.DateTime, nullable=True),
        sa.Column("failed_login_attempts", sa.Integer, default=0),
        sa.Column("locked_until", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # permisos table
    op.create_table(
        "permisos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=True),
        sa.Column("categoria", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # rol_permisos table
    op.create_table(
        "rol_permisos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rol",
            sa.Enum("ADMINISTRADOR", "DOCENTE", "APOYO", name="rolenum", create_type=False),
            nullable=False,
            index=True,
        ),
        sa.Column("permiso_codigo", sa.String(50), nullable=False),
        sa.Column("tiene_permiso", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # user_permisos table
    op.create_table(
        "user_permisos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("permiso_codigo", sa.String(50), nullable=False, index=True),
        sa.Column("tiene_permiso", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("token", sa.String(500), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("is_revoked", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # estudiantes table
    op.create_table(
        "estudiantes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column("nombres", sa.String(255), nullable=False),
        sa.Column("apellidos", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("documento", sa.String(50), nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("programa", sa.String(255), nullable=False),
        sa.Column("semestre", sa.Integer, default=1),
        sa.Column("promedio_general", sa.Numeric(4, 2), nullable=True),
        sa.Column("promedio_acumulado", sa.Numeric(4, 2), nullable=True),
        sa.Column(
            "estado",
            sa.Enum("ACTIVO", "INACTIVO", "GRADUADO", "SUSPENDIDO", name="estadoestudiante"),
            default="ACTIVO",
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # materias table
    op.create_table(
        "materias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("codigo", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("programa", sa.String(255), nullable=True),
        sa.Column("creditos", sa.Integer, default=0),
        sa.Column("activo", sa.String(10), default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # inscripciones table
    op.create_table(
        "inscripciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "estudiante_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("estudiantes.id"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materias.id"),
            nullable=False,
        ),
        sa.Column("periodo", sa.String(20), nullable=False, index=True),
        sa.Column("nota_final", sa.Numeric(5, 2), nullable=True),
        sa.Column("nota1", sa.Numeric(5, 2), nullable=True),
        sa.Column("nota2", sa.Numeric(5, 2), nullable=True),
        sa.Column("nota3", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "estado",
            sa.Enum("APROBADO", "REPROBADO", "EN_CURSO", "CANCELADO", name="estadoinscripcion"),
            default="EN_CURSO",
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # alertas table
    op.create_table(
        "alertas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "estudiante_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("estudiantes.id"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materias.id"),
            nullable=True,
        ),
        sa.Column(
            "nivel_riesgo",
            sa.Enum("ROJO", "AMARILLO", "VERDE", name="nivelriesgo"),
            nullable=False,
        ),
        sa.Column(
            "estado_seguimiento",
            sa.Enum("PENDIENTE", "EN_PROCESO", "RESUELTO", "DESCARTADO", name="estadoseguimiento"),
            default="PENDIENTE",
        ),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("periodo", sa.String(20), nullable=False, index=True),
        sa.Column("promedio_anterior", sa.Numeric(4, 2), nullable=True),
        sa.Column("promedio_actual", sa.Numeric(4, 2), nullable=True),
        sa.Column("promedio_proyeccion", sa.Numeric(4, 2), nullable=True),
        sa.Column("docentes_notificados", postgresql.JSON, server_default="[]"),
        sa.Column("notificaciones_enviadas", postgresql.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # actividades table
    op.create_table(
        "actividades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "alerta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alertas.id"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column(
            "tipo",
            sa.Enum("LLAMADA", "VISITA", "REUNION", "EMAIL", "OTRO", name="tipoactividad"),
            nullable=False,
        ),
        sa.Column("resultado", sa.Text, nullable=True),
        sa.Column("fecha_actividad", sa.DateTime, nullable=False),
        sa.Column("completada", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # encuestas table
    op.create_table(
        "encuestas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("preguntas", postgresql.JSON, server_default="[]"),
        sa.Column("estado", sa.String(20), server_default="BORRADOR"),
        sa.Column("periodo", sa.String(20), nullable=True),
        sa.Column("fecha_inicio", sa.DateTime, nullable=True),
        sa.Column("fecha_fin", sa.DateTime, nullable=True),
        sa.Column("es_publica", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # respuestas_encuestas table
    op.create_table(
        "respuestas_encuestas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "encuesta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("encuestas.id"),
            nullable=False,
        ),
        sa.Column(
            "estudiante_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("estudiantes.id"),
            nullable=False,
        ),
        sa.Column("respuestas", postgresql.JSON, server_default="{}"),
        sa.Column("fecha_respuesta", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # artefactos table
    op.create_table(
        "artefactos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "alerta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alertas.id"),
            nullable=True,
        ),
        sa.Column(
            "estudiante_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("estudiantes.id"),
            nullable=True,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # parametrizacion table
    op.create_table(
        "parametrizacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clave", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("valor", sa.Text, nullable=True),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("tipo", sa.String(20), server_default="texto"),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # auditoria table
    op.create_table(
        "auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accion", sa.String(100), nullable=False, index=True),
        sa.Column("entidad", sa.String(50), nullable=False, index=True),
        sa.Column("entidad_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detalles", postgresql.JSON, nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("estado", sa.String(20), server_default="EXITOSO"),
        sa.Column("mensaje", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("auditoria")
    op.drop_table("parametrizacion")
    op.drop_table("artefactos")
    op.drop_table("respuestas_encuestas")
    op.drop_table("encuestas")
    op.drop_table("actividades")
    op.drop_table("alertas")
    op.drop_table("inscripciones")
    op.drop_table("materias")
    op.drop_table("estudiantes")
    op.drop_table("refresh_tokens")
    op.drop_table("user_permisos")
    op.drop_table("rol_permisos")
    op.drop_table("permisos")
    op.drop_table("users")

    # drop enum types
    op.execute("DROP TYPE IF EXISTS rolenum")
    op.execute("DROP TYPE IF EXISTS estadoestudiante")
    op.execute("DROP TYPE IF EXISTS estadoinscripcion")
    op.execute("DROP TYPE IF EXISTS nivelriesgo")
    op.execute("DROP TYPE IF EXISTS estadoseguimiento")
    op.execute("DROP TYPE IF EXISTS tipoactividad")
