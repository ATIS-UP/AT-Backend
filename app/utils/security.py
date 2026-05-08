"""Utilidades de seguridad: encriptación y hashing"""
from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib

from app.config import settings

# Contexto para hashing de contraseñas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fernet para encriptación de datos sensibles
fernet = Fernet(settings.FERNET_KEY.encode())


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
        return ""  # Datos no encriptados o corruptos
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