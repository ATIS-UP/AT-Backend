"""Modelos de Alertas, Actividades, Encuestas y Artefactos"""
import uuid
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Enum, ForeignKey, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class NivelRiesgo(str, enum.Enum):
    ROJO = "ROJO"       # Crítico - perder materia
    AMARILLO = "AMARILLO"  # Medio - riesgo de perder
    VERDE = "VERDE"     # Bajo - monitor


class EstadoSeguimiento(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_PROCESO = "EN_PROCESO"
    RESUELTO = "RESUELTO"
    DESCARTADO = "DESCARTADO"


class TipoActividad(str, enum.Enum):
    LLAMADA = "LLAMADA"
    VISITA = "VISITA"
    REUNION = "REUNION"
    EMAIL = "EMAIL"
    OTRO = "OTRO"


class Alerta(Base):
    __tablename__ = "alertas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estudiante_id = Column(UUID(as_uuid=True), ForeignKey("estudiantes.id"), nullable=False)
    materia_id = Column(UUID(as_uuid=True), ForeignKey("materias.id"), nullable=True)
    nivel_riesgo = Column(Enum(NivelRiesgo), nullable=False)
    estado_seguimiento = Column(Enum(EstadoSeguimiento), default=EstadoSeguimiento.PENDIENTE)
    descripcion = Column(Text, nullable=True)
    periodo = Column(String(20), nullable=False, index=True)  # ej: "2025-1"

    # Datos encriptados
    promedio_anterior = Column(Numeric(4, 2), nullable=True)  # Encriptado
    promedio_actual = Column(Numeric(4, 2), nullable=True)  # Encriptado
    promedio_proyeccion = Column(Numeric(4, 2), nullable=True)  # Encriptado

    docentes_notificados = Column(JSON, default=list)
    notificaciones_enviadas = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    estudiante = relationship("Estudiante", back_populates="alertas")
    materia = relationship("Materia", back_populates="alertas")
    actividades = relationship("Actividad", back_populates="alerta", cascade="all, delete-orphan")
    artefactos = relationship("Artefacto", back_populates="alerta")


class Actividad(Base):
    __tablename__ = "actividades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alerta_id = Column(UUID(as_uuid=True), ForeignKey("alertas.id"), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(Enum(TipoActividad), nullable=False)
    resultado = Column(Text, nullable=True)
    fecha_actividad = Column(DateTime, nullable=False)
    completada = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    alerta = relationship("Alerta", back_populates="actividades")
    usuario = relationship("User", back_populates="actividades")


class Encuesta(Base):
    __tablename__ = "encuestas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    preguntas = Column(JSON, default=list)  # [{"id": 1, "pregunta": "...", "tipo": "opcion"}]
    estado = Column(String(20), default="BORRADOR")  # BORRADOR, PUBLICADA, CERRADA
    periodo = Column(String(20), nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    es_publica = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    respuestas = relationship("RespuestaEncuesta", back_populates="encuesta")


class RespuestaEncuesta(Base):
    __tablename__ = "respuestas_encuestas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encuesta_id = Column(UUID(as_uuid=True), ForeignKey("encuestas.id"), nullable=False)
    estudiante_id = Column(UUID(as_uuid=True), ForeignKey("estudiantes.id"), nullable=False)
    respuestas = Column(JSON, default=dict)  # {"pregunta_1": "respuesta", ...}
    fecha_respuesta = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())

    # Relaciones
    encuesta = relationship("Encuesta", back_populates="respuestas")
    estudiante = relationship("Estudiante", back_populates="respuestas_encuestas")


class Artefacto(Base):
    __tablename__ = "artefactos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alerta_id = Column(UUID(as_uuid=True), ForeignKey("alertas.id"), nullable=True)
    estudiante_id = Column(UUID(as_uuid=True), ForeignKey("estudiantes.id"), nullable=True)
    nombre = Column(String(255), nullable=False)
    tipo = Column(String(50), nullable=False)  # DOCUMENTO, IMAGEN, PDF, OTRO
    url = Column(String(500), nullable=False)
    descripcion = Column(Text, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relaciones
    alerta = relationship("Alerta", back_populates="artefactos")
    estudiante = relationship("Estudiante", back_populates="artefactos")
    usuario = relationship("User")