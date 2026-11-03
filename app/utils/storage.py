"""Almacenamiento de archivos subidos: disco local (dev) o MinIO/S3 (prod) según STORAGE_BACKEND.

Las claves son rutas relativas con "/" (p. ej. "uploads/anexos_actividades/2026/06/x.png").
En local se resuelven contra UPLOAD_BASE_PATH; en S3 se usan tal cual como Key del bucket.
"""
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError
from fastapi import Response

from app.config import settings


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
    )


def _ruta_local(key: str) -> Path:
    base = Path(settings.UPLOAD_BASE_PATH).resolve()
    ruta = (base / key).resolve()
    if not ruta.is_relative_to(base):
        raise ValueError(f"clave de almacenamiento fuera de UPLOAD_BASE_PATH: {key}")
    return ruta


def guardar(key: str, contenido: bytes, content_type: str) -> None:
    if _usa_s3():
        _s3_client().put_object(
            Bucket=settings.MINIO_BUCKET, Key=key, Body=contenido, ContentType=content_type,
        )
        return

    ruta = _ruta_local(key)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


def leer(key: str) -> bytes | None:
    """Devuelve el contenido del archivo, o None si no existe."""
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
