"""Modelos de Actividades Institucionales"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class TipoActividadInstitucional(str, enum.Enum):
    CLASE = "CLASE"
    REFUERZO = "REFUERZO"
    TORNEO = "TORNEO"
    TALLER = "TALLER"
    SEMINARIO = "SEMINARIO"
    TUTORIA = "TUTORIA"
    OTRO = "OTRO"


class EstadoActividadInstitucional(str, enum.Enum):
    CREADA = "CREADA"
    EN_CURSO = "EN_CURSO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class ModalidadActividad(str, enum.Enum):
    PRESENCIAL = "PRESENCIAL"
    VIRTUAL = "VIRTUAL"
    HIBRIDA = "HIBRIDA"


class ActividadInstitucional(Base):
    __tablename__ = "actividades_institucionales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(Enum(TipoActividadInstitucional), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    estado = Column(Enum(EstadoActividadInstitucional), nullable=False, default=EstadoActividadInstitucional.CREADA)
    descripcion = Column(Text, nullable=False)
    encargado = Column(String(255), nullable=False)
    observaciones = Column(Text, nullable=True)
    anexos = Column(Text, nullable=True)
    creador_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modalidad = Column(Enum(ModalidadActividad), nullable=False)
    lugar_enlace = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    creador = relationship("User", foreign_keys=[creador_id])
    archivos_anexos = relationship("AnexoActividad", back_populates="actividad", cascade="all, delete-orphan")
