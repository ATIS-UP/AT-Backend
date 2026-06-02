"""Modelo de Novedades para Casos Especiales"""
import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class NovedadCaso(Base):
    __tablename__ = "novedades_casos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_caso = Column(String(50), nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    orden = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
