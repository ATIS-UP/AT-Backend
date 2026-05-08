"""Utilidades de autenticación JWT"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

from app.config import settings
from app.models.user import User, RefreshToken
from app.database import SessionLocal


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> tuple[str, datetime]:
    """Crea un JWT refresh token"""
    expires = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expires, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, expires


def decode_token(token: str) -> dict:
    """Decodifica un JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verifica y decodifica un token"""
    payload = decode_token(token)
    if not payload:
        return None

    if payload.get("type") != token_type:
        return None

    return payload


def save_refresh_token(user_id: str, token: str, expires_at: datetime) -> RefreshToken:
    """Guarda el refresh token en la base de datos"""
    db = SessionLocal()
    try:
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        db.add(refresh_token)
        db.commit()
        db.refresh(refresh_token)
        return refresh_token
    finally:
        db.close()


def revoke_refresh_token(token: str) -> bool:
    """Revoca un refresh token"""
    db = SessionLocal()
    try:
        refresh = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if refresh:
            refresh.is_revoked = True
            db.commit()
            return True
        return False
    finally:
        db.close()


def is_refresh_token_valid(token: str, user_id: str) -> bool:
    """Verifica si un refresh token es válido"""
    db = SessionLocal()
    try:
        refresh = db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        return refresh is not None
    finally:
        db.close()


def revoke_all_user_tokens(user_id: str) -> bool:
    """Revoca todos los refresh tokens de un usuario"""
    db = SessionLocal()
    try:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).update({"is_revoked": True})
        db.commit()
        return True
    finally:
        db.close()