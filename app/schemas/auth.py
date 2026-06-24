"""Schemas de autenticación"""
from pydantic import BaseModel
from pydantic import ConfigDict, EmailStr, Field
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
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    usuario: Optional["UserResponse"] = None
    mfa_required: bool = False
    temp_token: Optional[str] = None
    mfa_methods: Optional[List[str]] = None


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
    mfa_enabled: bool = False
    mfa_methods: List[str] = []
    last_login: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


# MFA Schemas
class MfaSetupResponse(BaseModel):
    secret: str
    uri: str
    qr_code_url: str


class MfaSetupRequest(BaseModel):
    methods: List[str] = Field(min_length=1)


class MfaVerifySetupRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)


class MfaVerifyLoginRequest(BaseModel):
    temp_token: str
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class MfaEmailOtpRequest(BaseModel):
    temp_token: str


class MfaEmailOtpVerifyRequest(BaseModel):
    temp_token: str
    email_code: str = Field(min_length=6, max_length=6)


class MfaBackupCodeVerifyRequest(BaseModel):
    temp_token: str
    backup_code: str


class MfaDisableRequest(BaseModel):
    password: str


class MfaStatusResponse(BaseModel):
    mfa_enabled: bool
    mfa_methods: List[str] = []


class MfaBackupCodesResponse(BaseModel):
    codes: List[str]
    remaining: int


class MfaBackupCodesLeftResponse(BaseModel):
    remaining: int


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
