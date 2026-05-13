"""Modelos de Registros de Casos Especiales"""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class TipoRegistroCaso(str, enum.Enum):
    SOCIO_ECONOMICO = "SOCIO_ECONOMICO"
    ARTICULADO = "ARTICULADO"
    RENDIMIENTO_ACADEMICO = "RENDIMIENTO_ACADEMICO"
    CONDUCTUAL = "CONDUCTUAL"
    OTRO = "OTRO"


class EstadoRegistroCaso(str, enum.Enum):
    ACTIVO = "ACTIVO"
    CERRADO = "CERRADO"
    PENDIENTE = "PENDIENTE"


class AccionHistorial(str, enum.Enum):
    APERTURA = "APERTURA"
    SEGUIMIENTO = "SEGUIMIENTO"
    CIERRE = "CIERRE"
    REAPERTURA = "REAPERTURA"


class RegistroCasoEspecial(Base):
    __tablename__ = "registros_casos_especiales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estudiante_id = Column(UUID(as_uuid=True), ForeignKey("estudiantes.id"), nullable=False, index=True)
    tipo = Column(Enum(TipoRegistroCaso), nullable=False)
    estado = Column(Enum(EstadoRegistroCaso), default=EstadoRegistroCaso.ACTIVO)
    observaciones = Column(Text, nullable=True)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    responsable_nombre = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    estudiante = relationship("Estudiante", foreign_keys=[estudiante_id])
    responsable = relationship("User", foreign_keys=[responsable_id])
    historiales = relationship("HistorialRegistro", back_populates="registro", cascade="all, delete-orphan")


class HistorialRegistro(Base):
    __tablename__ = "historial_registros"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registro_id = Column(UUID(as_uuid=True), ForeignKey("registros_casos_especiales.id"), nullable=False, index=True)
    accion = Column(String(50), nullable=False)
    observaciones = Column(Text, nullable=True)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    responsable_nombre = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    registro = relationship("RegistroCasoEspecial", back_populates="historiales")
    responsable = relationship("User", foreign_keys=[responsable_id])