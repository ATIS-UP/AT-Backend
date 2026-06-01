"""Modelo de registros TCBU (Tasa de Cobertura de Bienestar Universitario)"""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


SERVICIOS_BIENESTAR = [
    "Cultural",
    "Inclusión",
    "Act. Física",
    "Salud",
    "Socioeconómica",
    "Espiritual",
    "Psicológica",
    "Odontología",
    "Alimentación",
    "SIMUP",
]


class BienestarRegistro(Base):
    __tablename__ = "bienestar_registros"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    periodo = Column(String(20), nullable=False, index=True)   # e.g. "2025-1"
    servicio = Column(String(50), nullable=False, index=True)  # one of SERVICIOS_BIENESTAR
    cantidad = Column(Integer, nullable=False, default=0)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("periodo", "servicio", name="uq_bienestar_periodo_servicio"),
    )
