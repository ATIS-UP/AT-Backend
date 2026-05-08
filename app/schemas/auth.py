"""Schemas de autenticación"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# Token responses
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str


# Login/Logout
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: "UserResponse"


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# User response
class UserResponse(BaseModel):
    id: str
    email: str
    nombre: str
    rol: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# User create (admin)
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str
    rol: str = "DOCENTE"
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    rol: Optional[str] = None
    is_active: Optional[bool] = None


# Permisos
class PermisoResponse(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str]
    categoria: str


class UserPermisoUpdate(BaseModel):
    permisos: List[dict]  # [{"codigo": "ver_estudiante", "tiene_permiso": true}]


class UserPermisosResponse(BaseModel):
    usuario_id: str
    rol: str
    permisos: List[str]  # Lista de códigos de permisos activos
    overrides: List[dict]  # Overrides específicos


# Actualizar forward reference
UserResponse.model_rebuild()