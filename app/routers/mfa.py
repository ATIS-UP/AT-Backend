"""router for multi-factor authentication (mfa)"""
import secrets
import logging
from datetime import datetime, timedelta
from datetime import UTC as tz_utc

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, EmailOtpCode, BackupCode
from app.schemas.auth import (
    MfaSetupResponse, MfaSetupRequest, MfaVerifySetupRequest, MfaVerifyLoginRequest,
    MfaEmailOtpRequest, MfaEmailOtpVerifyRequest, MfaBackupCodeVerifyRequest,
    MfaDisableRequest, MfaStatusResponse, MfaBackupCodesResponse,
    MfaBackupCodesLeftResponse, UserResponse
)
from app.utils.auth import (
    create_access_token, create_refresh_token, create_temp_token,
    save_refresh_token, verify_token
)
from app.utils.security import (
    hash_password, verify_password, encrypt_data, decrypt_data, hash_data
)
from app.utils.email import EmailService
from app.utils.audit import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/mfa", tags=["mfa"])

BACKUP_CODE_COUNT = 8
BACKUP_CODE_LENGTH = 10

VALID_METHODS = {"totp", "email", "backup_codes"}


def _generate_backup_codes() -> list[str]:
    """Generate cryptographically secure backup codes."""
    codes = []
    for _ in range(BACKUP_CODE_COUNT):
        code = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(BACKUP_CODE_LENGTH))
        formatted = f"{code[:4]}-{code[4:]}"
        codes.append(formatted)
    return codes


@router.post("/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    data: MfaSetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate TOTP secret and provisioning URI for authenticator app."""
    invalid = [m for m in data.methods if m not in VALID_METHODS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Métodos inválidos: {', '.join(invalid)}")

    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA ya está activo. Desactívelo para reconfigurar.")

    current_user.mfa_methods = data.methods

    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="SATISUP"
    )

    current_user.mfa_secret = encrypt_data(secret) if "totp" in data.methods else None
    if "totp" not in data.methods:
        current_user.mfa_enabled = True
    db.commit()

    return MfaSetupResponse(
        secret=secret,
        uri=uri,
        qr_code_url=uri
    )


@router.post("/verify-setup")
async def verify_setup(
    data: MfaVerifySetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify TOTP code and enable MFA for the user."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="Primero debe generar un secreto MFA")

    secret = decrypt_data(current_user.mfa_secret)
    totp = pyotp.TOTP(secret)

    if not totp.verify(data.totp_code, valid_window=1):
        raise HTTPException(status_code=400, detail="Código inválido. Escanee el QR nuevamente e intente de nuevo.")

    current_user.mfa_enabled = True
    db.commit()

    return {"message": "Autenticación multifactor activada exitosamente"}


@router.put("/methods")
async def update_mfa_methods(
    data: MfaSetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update MFA methods. If empty, disable MFA completely."""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA no está activo. Actívelo primero.")

    if not data.methods:
        current_user.mfa_secret = None
        current_user.mfa_enabled = False
        current_user.mfa_methods = []
        db.query(EmailOtpCode).filter(
            EmailOtpCode.user_id == current_user.id,
            EmailOtpCode.is_used == False
        ).update({"is_used": True})
        db.query(BackupCode).filter(
            BackupCode.user_id == current_user.id
        ).delete()
        db.commit()
        return {"message": "MFA desactivado (sin métodos seleccionados)", "methods": []}

    invalid = [m for m in data.methods if m not in VALID_METHODS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Métodos inválidos: {', '.join(invalid)}")

    current_user.mfa_methods = data.methods
    db.commit()

    return {"message": "Métodos MFA actualizados", "methods": data.methods}


@router.get("/status", response_model=MfaStatusResponse)
async def get_mfa_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get MFA status for the current user."""
    return MfaStatusResponse(
        mfa_enabled=current_user.mfa_enabled,
        mfa_methods=current_user.mfa_methods or []
    )


@router.post("/disable")
async def disable_mfa(
    data: MfaDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disable MFA (requires password confirmation)."""
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta")

    current_user.mfa_secret = None
    current_user.mfa_enabled = False
    current_user.mfa_methods = []

    db.query(EmailOtpCode).filter(
        EmailOtpCode.user_id == current_user.id,
        EmailOtpCode.is_used == False
    ).update({"is_used": True})

    db.query(BackupCode).filter(
        BackupCode.user_id == current_user.id
    ).delete()

    db.commit()
    return {"message": "Autenticación multifactor desactivada"}


@router.get("/backup-codes", response_model=MfaBackupCodesLeftResponse)
async def get_backup_codes_left(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get count of remaining unused backup codes."""
    remaining = db.query(BackupCode).filter(
        BackupCode.user_id == current_user.id,
        BackupCode.is_used == False
    ).count()
    return MfaBackupCodesLeftResponse(remaining=remaining)


@router.post("/generate-backup-codes", response_model=MfaBackupCodesResponse)
async def generate_backup_codes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new set of backup codes (invalidates previous set)."""
    db.query(BackupCode).filter(
        BackupCode.user_id == current_user.id
    ).delete()

    codes = _generate_backup_codes()
    for code in codes:
        db.add(BackupCode(
            user_id=current_user.id,
            code_hash=hash_password(code)
        ))
    db.commit()

    return MfaBackupCodesResponse(codes=codes, remaining=BACKUP_CODE_COUNT)


def _verify_temp_token(temp_token: str, db: Session) -> User:
    """Verify a temp token and return the user."""
    payload = verify_token(temp_token, "mfa")
    if not payload:
        raise HTTPException(status_code=401, detail="Token temporal inválido o expirado. Inicie sesión nuevamente.")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    return user


def _issue_tokens(user: User, db: Session) -> dict:
    """Issue access and refresh tokens for a user after MFA verification."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(tz_utc)

    token_data = {"sub": str(user.id), "email": user.email, "rol": user.rol.value}
    access_token = create_access_token(token_data)
    refresh_token, expires_at = create_refresh_token({"sub": str(user.id)})

    save_refresh_token(db, str(user.id), refresh_token, expires_at)
    AuditService.log_login(db, str(user.id), user.email, True, None)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "usuario": UserResponse(
            id=str(user.id),
            email=user.email,
            nombre=user.nombre,
            rol=user.rol.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            mfa_methods=user.mfa_methods or [],
            last_login=user.last_login,
            created_at=user.created_at
        )
    }


@router.post("/verify")
async def verify_mfa_login(
    data: MfaVerifyLoginRequest,
    db: Session = Depends(get_db),
):
    """Verify TOTP code after initial login (step 2 of MFA)."""
    user = _verify_temp_token(data.temp_token, db)

    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA no está habilitado para este usuario")

    if not data.totp_code:
        raise HTTPException(status_code=400, detail="Código TOTP requerido")

    secret = decrypt_data(user.mfa_secret)
    totp = pyotp.TOTP(secret)

    if not totp.verify(data.totp_code, valid_window=1):
        AuditService.log_login(db, str(user.id), user.email, False, None)
        db.commit()
        raise HTTPException(status_code=401, detail="Código de verificación inválido")

    tokens = _issue_tokens(user, db)
    return tokens


@router.post("/email-otp")
async def send_email_otp(
    data: MfaEmailOtpRequest,
    db: Session = Depends(get_db),
):
    """Send a one-time code to the user's email as a backup MFA method."""
    user = _verify_temp_token(data.temp_token, db)

    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA no está habilitado para este usuario")

    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = hash_password(code)

    db.query(EmailOtpCode).filter(
        EmailOtpCode.user_id == user.id,
        EmailOtpCode.is_used == False
    ).update({"is_used": True})

    otp_record = EmailOtpCode(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=datetime.now(tz_utc) + timedelta(minutes=3)
    )
    db.add(otp_record)
    db.commit()

    sent = EmailService.send_otp(user.email, code)
    if not sent:
        raise HTTPException(status_code=500, detail="Error al enviar el código. Intente nuevamente.")

    return {"message": "Código enviado a su correo institucional"}


@router.post("/verify-email-otp")
async def verify_email_otp(
    data: MfaEmailOtpVerifyRequest,
    db: Session = Depends(get_db),
):
    """Verify a one-time code sent by email as backup MFA."""
    user = _verify_temp_token(data.temp_token, db)

    otp_record = db.query(EmailOtpCode).filter(
        EmailOtpCode.user_id == user.id,
        EmailOtpCode.is_used == False,
        EmailOtpCode.expires_at > datetime.now(tz_utc)
    ).order_by(EmailOtpCode.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(status_code=401, detail="No hay un código válido. Solicite uno nuevo.")

    if not verify_password(data.email_code, otp_record.code_hash):
        raise HTTPException(status_code=401, detail="Código inválido")

    otp_record.is_used = True
    tokens = _issue_tokens(user, db)
    return tokens


@router.post("/verify-backup-code")
async def verify_backup_code(
    data: MfaBackupCodeVerifyRequest,
    db: Session = Depends(get_db),
):
    """Verify a backup code as MFA method."""
    user = _verify_temp_token(data.temp_token, db)

    backup_code = db.query(BackupCode).filter(
        BackupCode.user_id == user.id,
        BackupCode.is_used == False
    ).all()

    for bc in backup_code:
        if verify_password(data.backup_code, bc.code_hash):
            bc.is_used = True
            tokens = _issue_tokens(user, db)
            return tokens

    raise HTTPException(status_code=401, detail="Código de respaldo inválido o ya utilizado")
