"""Modelos de Parametrización y Auditoría"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Parametrizacion(Base):
    __tablename__ = "parametrizacion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clave = Column(String(100), unique=True, nullable=False, index=True)
    valor = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(20), default="texto")  # texto, numero, json, booleano
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), nullable=True)
    accion = Column(String(100), nullable=False, index=True)
    entidad = Column(String(50), nullable=False, index=True)
    entidad_id = Column(UUID(as_uuid=True), nullable=True)
    detalles = Column(JSON, nullable=True)
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    estado = Column(String(20), default="EXITOSO")
    mensaje = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)