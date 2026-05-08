"""Modelos de Estudiantes, Materias e Inscripciones"""
import uuid
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class EstadoEstudiante(str, enum.Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    GRADUADO = "GRADUADO"
    SUSPENDIDO = "SUSPENDIDO"


class EstadoInscripcion(str, enum.Enum):
    APROBADO = "APROBADO"
    REPROBADO = "REPROBADO"
    EN_CURSO = "EN_CURSO"
    CANCELADO = "CANCELADO"


class Estudiante(Base):
    __tablename__ = "estudiantes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(20), unique=True, nullable=False, index=True)

    # Datos encriptados con Fernet
    nombres = Column(String(255), nullable=False)  # Encriptado
    apellidos = Column(String(255), nullable=False)  # Encriptado
    email = Column(String(255), nullable=True)  # Encriptado
    documento = Column(String(50), nullable=True)  # Encriptado
    telefono = Column(String(20), nullable=True)  # Encriptado

    # Datos no encriptados
    programa = Column(String(255), nullable=False)
    semestre = Column(Integer, default=1)
    promedio_general = Column(Numeric(4, 2), nullable=True)  # Encriptado
    promedio_acumulado = Column(Numeric(4, 2), nullable=True)  # Encriptado
    estado = Column(Enum(EstadoEstudiante), default=EstadoEstudiante.ACTIVO)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    alertas = relationship("Alerta", back_populates="estudiante")
    inscripciones = relationship("Inscripcion", back_populates="estudiante")
    artefactos = relationship("Artefacto", back_populates="estudiante")
    respuestas_encuestas = relationship("RespuestaEncuesta", back_populates="estudiante")


class Materia(Base):
    __tablename__ = "materias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    programa = Column(String(255), nullable=True)
    creditos = Column(Integer, default=0)
    activo = Column(String(10), default="true")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    inscripciones = relationship("Inscripcion", back_populates="materia")
    alertas = relationship("Alerta", back_populates="materia")


class Inscripcion(Base):
    __tablename__ = "inscripciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estudiante_id = Column(UUID(as_uuid=True), ForeignKey("estudiantes.id"), nullable=False)
    materia_id = Column(UUID(as_uuid=True), ForeignKey("materias.id"), nullable=False)
    periodo = Column(String(20), nullable=False, index=True)  # ej: "2025-1"
    nota_final = Column(Numeric(5, 2), nullable=True)  # Encriptado
    nota1 = Column(Numeric(5, 2), nullable=True)  # Encriptado
    nota2 = Column(Numeric(5, 2), nullable=True)  # Encriptado
    nota3 = Column(Numeric(5, 2), nullable=True)  # Encriptado
    estado = Column(Enum(EstadoInscripcion), default=EstadoInscripcion.EN_CURSO)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    estudiante = relationship("Estudiante", back_populates="inscripciones")
    materia = relationship("Materia", back_populates="inscripciones")