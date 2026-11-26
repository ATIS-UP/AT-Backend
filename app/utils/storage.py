"""Almacenamiento de archivos subidos: disco local (dev) o MinIO/S3 (prod) según STORAGE_BACKEND.

Las claves son rutas relativas con "/" (p. ej. "uploads/anexos_actividades/2026/06/x.png").
En local se resuelven contra UPLOAD_BASE_PATH; en S3 se usan tal cual como Key del bucket.

El contenido se guarda cifrado con la FERNET_KEY y lleva el prefijo PREFIJO_CIFRADO.
Los archivos sin ese prefijo (subidos antes del cifrado) se leen tal cual.
"""
import logging
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from cryptography.fernet import InvalidToken
from fastapi import Response

from app.config import settings
from app.utils.security import fernet

logger = logging.getLogger(__name__)

# Marca los archivos cifrados; el número es la versión del formato.
PREFIJO_CIFRADO = b"SATISENC1:"

# Sin esto boto3 espera 60 s por intento: un MinIO caído retendría cada petición minutos.
_S3_CONFIG = Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 2})


def _usa_s3() -> bool:
    return settings.STORAGE_BACKEND == "s3"


def _s3_client():
    esquema = "https" if settings.MINIO_USE_SSL else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{esquema}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        use_ssl=settings.MINIO_USE_SSL,
        config=_S3_CONFIG,
    )


def _ruta_local(key: str) -> Path:
    base = Path(settings.UPLOAD_BASE_PATH).resolve()
    ruta = (base / key).resolve()
    if not ruta.is_relative_to(base):
        raise ValueError(f"clave de almacenamiento fuera de UPLOAD_BASE_PATH: {key}")
    return ruta


def _cifrar(contenido: bytes) -> bytes:
    return PREFIJO_CIFRADO + fernet.encrypt(contenido)


def _descifrar(key: str, almacenado: bytes) -> bytes:
    if not almacenado.startswith(PREFIJO_CIFRADO):
        return almacenado  # archivo anterior al cifrado
    try:
        return fernet.decrypt(almacenado[len(PREFIJO_CIFRADO):])
    except InvalidToken:
        logger.error("No se pudo descifrar %s: la FERNET_KEY no coincide o el archivo está dañado", key)
        raise RuntimeError(f"no se pudo descifrar el archivo {key}")


def guardar(key: str, contenido: bytes, content_type: str) -> None:
    contenido = _cifrar(contenido)

    if _usa_s3():
        _s3_client().put_object(
            Bucket=settings.MINIO_BUCKET, Key=key, Body=contenido, ContentType=content_type,
        )
        return

    ruta = _ruta_local(key)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


def leer(key: str) -> bytes | None:
    """Devuelve el contenido descifrado del archivo, o None si no existe."""
    almacenado = _leer_almacenado(key)
    return None if almacenado is None else _descifrar(key, almacenado)


def _leer_almacenado(key: str) -> bytes | None:
    if _usa_s3():
        try:
            objeto = _s3_client().get_object(Bucket=settings.MINIO_BUCKET, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise
        return objeto["Body"].read()

    ruta = _ruta_local(key)
    return ruta.read_bytes() if ruta.is_file() else None


def eliminar(key: str) -> None:
    """Borra el archivo; no falla si ya no existe."""
    if _usa_s3():
        try:
            _s3_client().delete_object(Bucket=settings.MINIO_BUCKET, Key=key)
        except ClientError:
            pass
        return

    _ruta_local(key).unlink(missing_ok=True)


def respuesta_archivo(
    contenido: bytes,
    nombre: str,
    media_type: str,
    headers: dict[str, str] | None = None,
) -> Response:
    """Respuesta de descarga con Content-Disposition compatible con nombres no ASCII."""
    nombre_codificado = quote(nombre)
    if nombre_codificado != nombre:
        disposition = f"attachment; filename*=utf-8''{nombre_codificado}"
    else:
        disposition = f'attachment; filename="{nombre}"'

    return Response(
        content=contenido,
        media_type=media_type,
        headers={"Content-Disposition": disposition, **(headers or {})},
    )
