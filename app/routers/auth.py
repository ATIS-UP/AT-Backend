"""router for authentication"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, RefreshToken
from app.schemas.auth import (
    LoginRequest, LoginResponse, LogoutRequest, RefreshTokenRequest,
    Token, UserResponse
)
from app.utils.auth import (
    create_access_token, create_refresh_token, verify_token,
    save_refresh_token, revoke_refresh_token, revoke_all_user_tokens,
    is_refresh_token_valid
)
from app.utils.security import verify_password, hash_password
from app.utils.permisos import PermisoService
from app.utils.audit import AuditService

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Inicio de sesión de usuario"""
    # Buscar usuario por email
    user = db.query(User).filter(User.email == login_data.email).first()

    # Verificar si el usuario existe y está activo
    if not user or not user.is_active:
        AuditService.log_login(db, None, login_data.email, False, request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    # Verificar si la cuenta está bloqueada
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta bloqueada. Intente más tarde."
        )

    # Verificar contraseña
    if not verify_password(login_data.password, user.password_hash):
        # Incrementar intentos fallidos
        user.failed_login_attempts += 1

        # Bloquear después de X intentos
        if user.failed_login_attempts >= 5:
            from datetime import timedelta
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
            AuditService.log_login(db, str(user.id), login_data.email, False, request.client.host)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Demasiados intentos fallidos. Cuenta bloqueada por 15 minutos."
            )

        db.commit()
        AuditService.log_login(db, str(user.id), login_data.email, False, request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    # Login exitoso - resetear contadores
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    # Crear tokens
    token_data = {"sub": str(user.id), "email": user.email, "rol": user.rol.value}
    access_token = create_access_token(token_data)
    refresh_token, expires_at = create_refresh_token({"sub": str(user.id)})

    # save refresh token using the endpoint's db session
    save_refresh_token(db, str(user.id), refresh_token, expires_at)
    db.commit()

    # audit log
    AuditService.log_login(db, str(user.id), login_data.email, True, request.client.host)

    # Obtener permisos del usuario
    permisos = PermisoService.get_permisos_usuario(db, user)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        usuario=UserResponse(
            id=str(user.id),
            email=user.email,
            nombre=user.nombre,
            rol=user.rol.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            created_at=user.created_at
        )
    )


@router.post("/logout")
async def logout(
    request: Request,
    logout_data: LogoutRequest = None,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Cierre de sesión"""
    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    user_id = payload.get("sub")

    # revoke specific refresh token if provided
    if logout_data and logout_data.refresh_token:
        revoke_refresh_token(db, logout_data.refresh_token)

    # revoke all tokens for the user
    revoke_all_user_tokens(db, user_id)
    db.commit()

    # audit log
    AuditService.log_logout(db, user_id, request.client.host)

    return {"message": "Logout exitoso"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """refresh access token with token rotation"""
    payload = verify_token(refresh_data.refresh_token, "refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado"
        )

    user_id = payload.get("sub")

    # verify the refresh token is valid and exists in db
    if not is_refresh_token_valid(db, refresh_data.refresh_token, user_id):
        # detect token reuse attack: if token exists but is revoked,
        # revoke all tokens for the user as a security measure
        existing = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_data.refresh_token,
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == True
        ).first()
        if existing:
            revoke_all_user_tokens(db, user_id)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revocado o expirado"
        )

    # get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo"
        )

    # revoke the old refresh token
    revoke_refresh_token(db, refresh_data.refresh_token)

    # issue a new refresh token
    new_refresh_token, new_expires = create_refresh_token({"sub": str(user.id)})
    save_refresh_token(db, str(user.id), new_refresh_token, new_expires)
    db.commit()

    # create new access token
    token_data = {"sub": str(user.id), "email": user.email, "rol": user.rol.value}
    access_token = create_access_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """get current authenticated user"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        nombre=current_user.nombre,
        rol=current_user.rol.value,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )


@router.get("/permisos")
async def get_permisos(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """get permissions for the current user"""
    permisos = PermisoService.get_permisos_usuario(db, current_user)

    return {
        "usuario_id": str(current_user.id),
        "rol": current_user.rol.value,
        "permisos": permisos
    }


@router.get("/permisos/{codigo}")
async def verificar_permiso(
    codigo: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """check if the current user has a specific permission"""
    tiene_permiso = PermisoService.tiene_permiso(db, current_user, codigo)

    return {
        "codigo": codigo,
        "tiene_permiso": tiene_permiso
    }


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


@router.put("/cambiar-password")
async def cambiar_password(
    data: CambiarPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """change password for the authenticated user"""
    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta",
        )

    current_user.password_hash = hash_password(data.password_nueva)
    db.commit()

    return {"message": "Contraseña actualizada exitosamente"}