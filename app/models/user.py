"""Modelos de Usuario y Permisos"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Table, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class RolEnum(str, enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    DOCENTE = "DOCENTE"
    APOYO = "APOYO"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=False)  # Encriptado
    rol = Column(Enum(RolEnum), default=RolEnum.DOCENTE, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    actividades = relationship("Actividad", back_populates="usuario")


class Permiso(Base):
    __tablename__ = "permisos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String(500), nullable=True)
    categoria = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rol = Column(Enum(RolEnum), nullable=False, index=True)
    permiso_codigo = Column(String(50), nullable=False)
    tiene_permiso = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class UserPermiso(Base):
    __tablename__ = "user_permisos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permiso_codigo = Column(String(50), nullable=False, index=True)
    tiene_permiso = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relaciones
    user = relationship("User")