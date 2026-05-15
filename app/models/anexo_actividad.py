"""Modelo de Anexos para Actividades Institucionales"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AnexoActividad(Base):
    __tablename__ = "anexos_actividades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actividad_id = Column(UUID(as_uuid=True), ForeignKey("actividades_institucionales.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(255), nullable=False)
    tipo = Column(String(50), nullable=False)
    url = Column(String(500), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    actividad = relationship("ActividadInstitucional", back_populates="archivos_anexos")
    usuario = relationship("User")
