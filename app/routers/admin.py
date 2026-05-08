"""Router de administración - gestión de usuarios y permisos"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, Permiso, UserPermiso, RolEnum
from app.schemas.auth import (
    UserCreate, UserUpdate, UserResponse, UserPermisoUpdate,
    UserPermisosResponse, PermisoResponse
)
from app.utils.auth import verify_token
from app.utils.security import hash_password
from app.utils.permisos import PermisoService
from app.utils.audit import AuditService

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBearer()


def get_current_user_with_permiso(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")
    return user


# ====== USUARIOS ======

@router.get("/usuarios", response_model=List[UserResponse])
async def list_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    buscar: str = Query(None),
    rol: str = Query(None)
):
    """Listar usuarios (solo admin)"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_usuarios"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    query = db.query(User)

    if buscar:
        query = query.filter(
            (User.email.ilike(f"%{buscar}%")) |
            (User.nombre.ilike(f"%{buscar}%"))
        )
    if rol:
        query = query.filter(User.rol == rol)

    usuarios = query.order_by(User.created_at.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    return [UserResponse(
        id=str(u.id),
        email=u.email,
        nombre=u.nombre,
        rol=u.rol.value,
        is_active=u.is_active,
        is_verified=u.is_verified,
        last_login=u.last_login,
        created_at=u.created_at
    ) for u in usuarios]


@router.get("/usuarios/{user_id}", response_model=UserResponse)
async def get_usuario(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener usuario por ID"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_usuarios"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

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


@router.post("/usuarios", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_usuario(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Crear un nuevo usuario (solo admin)"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_usuarios"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    # Verificar que el email no exista
    existente = db.query(User).filter(User.email == user_data.email).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya está en uso")

    # Crear usuario
    nuevo = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        nombre=user_data.nombre,
        rol=RolEnum(user_data.rol),
        is_active=user_data.is_active
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    AuditService.log_crear(db, str(current_user.id), "Usuario", str(nuevo.id),
                          {"email": nuevo.email, "rol": nuevo.rol.value}, request.client.host)

    return UserResponse(
        id=str(nuevo.id),
        email=nuevo.email,
        nombre=nuevo.nombre,
        rol=nuevo.rol.value,
        is_active=nuevo.is_active,
        is_verified=nuevo.is_verified,
        last_login=nuevo.last_login,
        created_at=nuevo.created_at
    )


@router.put("/usuarios/{user_id}", response_model=UserResponse)
async def update_usuario(
    user_id: str,
    user_data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Actualizar un usuario"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_usuarios"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    update_data = user_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "rol" and value:
            value = RolEnum(value)
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    AuditService.log_actualizar(db, str(current_user.id), "Usuario", user_id,
                               {"email": user.email}, update_data, request.client.host)

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


@router.delete("/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_usuario(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Eliminar un usuario (soft delete - desactivar)"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_usuarios"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # No permitir eliminarse a sí mismo
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes eliminarte a ti mismo")

    user.is_active = False
    db.commit()

    AuditService.log_eliminar(db, str(current_user.id), "Usuario", user_id,
                              {"email": user.email}, request.client.host)

    return None


# ====== PERMISOS ======

@router.get("/permisos", response_model=dict)
async def get_all_permisos(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener todos los permisos del catálogo"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_usuarios"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    return PermisoService.get_permisos_por_categoria(db)


@router.get("/usuarios/{user_id}/permisos", response_model=UserPermisosResponse)
async def get_usuario_permisos(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener permisos de un usuario específico"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_usuarios"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    permisos = PermisoService.get_permisos_usuario(db, user)

    # Obtener overrides
    overrides = db.query(UserPermiso).filter(UserPermiso.user_id == user_id).all()
    overrides_list = [{"codigo": o.permiso_codigo, "tiene_permiso": o.tiene_permiso} for o in overrides]

    return UserPermisosResponse(
        usuario_id=str(user.id),
        rol=user.rol.value,
        permisos=permisos,
        overrides=overrides_list
    )


@router.put("/usuarios/{user_id}/permisos", response_model=UserPermisosResponse)
async def update_usuario_permisos(
    user_id: str,
    permisos_data: UserPermisoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Actualizar permisos de un usuario (overrides)"""
    if not PermisoService.tiene_permiso(db, current_user, "gestionar_permisos"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Actualizar overrides
    for perm in permisos_data.permisos:
        PermisoService.set_permiso_usuario(db, user_id, perm["codigo"], perm["tiene_permiso"])

    # Retornar permisos actualizados
    permisos = PermisoService.get_permisos_usuario(db, user)
    overrides = db.query(UserPermiso).filter(UserPermiso.user_id == user_id).all()
    overrides_list = [{"codigo": o.permiso_codigo, "tiene_permiso": o.tiene_permiso} for o in overrides]

    AuditService.log_actualizar(db, str(current_user.id), "UserPermisos", user_id,
                               {}, {"permisos": permisos_data.permisos}, request.client.host)

    return UserPermisosResponse(
        usuario_id=str(user.id),
        rol=user.rol.value,
        permisos=permisos,
        overrides=overrides_list
    )