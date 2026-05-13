"""Utilidades de seguridad: encriptación y hashing"""
import logging

from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib

from app.config import settings

logger = logging.getLogger(__name__)

# Contexto para hashing de contraseñas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Validate Fernet key at startup
try:
    if not settings.FERNET_KEY:
        raise ValueError("FERNET_KEY environment variable is not set")
    fernet = Fernet(settings.FERNET_KEY.encode())
    logger.info("Fernet encryption key loaded successfully")
except Exception as e:
    logger.error(f"Failed to initialize Fernet key: {e}")
    raise RuntimeError(f"Invalid FERNET_KEY configuration: {e}")


def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)


def encrypt_data(data: str) -> str:
    """Encripta datos sensibles usando Fernet"""
    if not data:
        return ""
    try:
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode()
    except Exception as e:
        raise ValueError(f"Error al encriptar: {str(e)}")


def decrypt_data(encrypted_data: str) -> str:
    """Desencripta datos sensibles usando Fernet"""
    if not encrypted_data:
        return ""
    try:
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except InvalidToken:
        data_preview = encrypted_data[:20] + "..." if len(encrypted_data) > 20 else encrypted_data
        logger.warning(f"Fernet decryption failed for data starting with: {data_preview}. This may indicate the data was encrypted with a different key.")
        return "[DATO_CORRUPTO]"
    except Exception as e:
        raise ValueError(f"Error al desencriptar: {str(e)}")


def encrypt_decrypt_field(value, operation: str):
    """
    Helper para encriptar/desencriptar campos de modelos
    operation: 'encrypt' o 'decrypt'
    """
    if value is None:
        return None
    if operation == 'encrypt':
        return encrypt_data(str(value))
    elif operation == 'decrypt':
        return decrypt_data(value)
    return value


def generate_encryption_key() -> str:
    """Genera una nueva clave de encriptación Fernet"""
    return Fernet.generate_key().decode()


def hash_data(data: str) -> str:
    """Genera un hash SHA-256 de datos"""
    return hashlib.sha256(data.encode()).hexdigest()


def sanitize_like_param(value: str, max_length: int = 200) -> str:
    """escape special characters for safe use in sql like filters"""
    if not value:
        return value
    value = value[:max_length]
    # escape sql like special chars
    value = value.replace("\\", "\\\\")
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")
    return value