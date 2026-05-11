"""jwt authentication utilities"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import RefreshToken


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """create a jwt access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> tuple[str, datetime]:
    """create a jwt refresh token"""
    expires = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expires, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, expires


def decode_token(token: str) -> dict:
    """decode a jwt token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """verify and decode a token, checking type matches"""
    payload = decode_token(token)
    if not payload:
        return None

    if payload.get("type") != token_type:
        return None

    return payload


def save_refresh_token(db: Session, user_id: str, token: str, expires_at: datetime) -> RefreshToken:
    """add a refresh token to the session (caller handles commit)"""
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(refresh_token)
    return refresh_token


def revoke_refresh_token(db: Session, token: str) -> bool:
    """mark a refresh token as revoked (caller handles commit)"""
    refresh = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if refresh:
        refresh.is_revoked = True
        return True
    return False


def is_refresh_token_valid(db: Session, token: str, user_id: str) -> bool:
    """check if a refresh token is valid and not expired or revoked"""
    refresh = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    return refresh is not None


def revoke_all_user_tokens(db: Session, user_id: str) -> bool:
    """revoke all active refresh tokens for a user (caller handles commit)"""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    return True