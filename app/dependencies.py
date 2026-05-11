"""centralized dependencies for authentication and authorization."""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.auth import verify_token
from app.utils.permisos import PermisoService
from app.exceptions import AuthenticationError, PermissionDeniedError

security = HTTPBearer()


async def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """verify jwt and return authenticated user"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise AuthenticationError()
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise AuthenticationError("Usuario inactivo o no encontrado")
    return user


def require_permiso(permiso_codigo: str):
    """factory: verify user has specific permission"""

    async def _check(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not PermisoService.tiene_permiso(db, current_user, permiso_codigo):
            raise PermissionDeniedError(permiso_codigo)
        return current_user

    return _check
