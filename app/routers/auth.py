"""Router de autenticación"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
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
from app.utils.security import verify_password
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

    # Guardar refresh token en DB
    save_refresh_token(str(user.id), refresh_token, expires_at)

    # Registrar auditoría
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

    # Revocar refresh token si se proporciona
    if logout_data and logout_data.refresh_token:
        revoke_refresh_token(logout_data.refresh_token)

    # Revocar todos los tokens del usuario
    revoke_all_user_tokens(user_id)

    # Auditoría
    AuditService.log_logout(db, user_id, request.client.host)

    return {"message": "Logout exitoso"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refrescar access token usando refresh token"""
    payload = verify_token(refresh_data.refresh_token, "refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado"
        )

    user_id = payload.get("sub")

    # Verificar que el refresh token sea válido y esté en la DB
    if not is_refresh_token_valid(refresh_data.refresh_token, user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revocado o expirado"
        )

    # Obtener usuario
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo"
        )

    # Crear nuevo access token
    token_data = {"sub": str(user.id), "email": user.email, "rol": user.rol.value}
    access_token = create_access_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Obtener usuario actual"""
    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        nombre=user.nombre,
        rol=user.rol.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login=user.last_login,
        created_at=user.created_at
    )


@router.get("/permisos")
async def get_permisos(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Obtener permisos del usuario actual"""
    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    permisos = PermisoService.get_permisos_usuario(db, user)

    return {
        "usuario_id": str(user.id),
        "rol": user.rol.value,
        "permisos": permisos
    }


@router.get("/permisos/{codigo}")
async def verificar_permiso(
    codigo: str,
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Verificar si el usuario tiene un permiso específico"""
    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    tiene_permiso = PermisoService.tiene_permiso(db, user, codigo)

    return {
        "codigo": codigo,
        "tiene_permiso": tiene_permiso
    }