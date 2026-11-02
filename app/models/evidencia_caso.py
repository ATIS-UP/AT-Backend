
"""Modelo de evidencias fotográficas de casos especiales."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EvidenciaCaso(Base):
    __tablename__ = "evidencias_casos"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    registro_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "registros_casos_especiales.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    nombre = Column(String(255), nullable=False)
    ruta = Column(String(500), nullable=False)
    tipo = Column(String(50), nullable=False)

    uploaded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )

    registro = relationship("RegistroCasoEspecial")
    usuario = relationship("User")
