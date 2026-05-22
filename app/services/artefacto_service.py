"""service for managing file artifacts (upload, list, download, delete)."""

import os
import uuid
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import EntityNotFoundError, ValidationError
from app.models.alerta import Artefacto
from app.models.estudiante import Estudiante, EstadoEstudiante
from app.utils.audit import AuditService


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}

MAX_FILE_SIZE = 10 * 1024 * 1024

UPLOAD_DIR = "uploads"

DOWNLOAD_TEMP_DIR = "/tmp/at-downloads"


class ArtefactoService:
    def __init__(self, db: Session):
        self.db = db
        self.storage_backend = settings.STORAGE_BACKEND

    def _get_s3_client(self):
        endpoint = (
            f"http://{settings.MINIO_ENDPOINT}"
            if not settings.MINIO_USE_SSL
            else f"https://{settings.MINIO_ENDPOINT}"
        )
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            use_ssl=settings.MINIO_USE_SSL,
        )

    def _validate_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise ValidationError("el nombre del archivo es requerido")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"tipo de archivo no permitido: {ext}. permitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                fields={"file": f"extension {ext} not allowed"},
            )

        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        if size > MAX_FILE_SIZE:
            raise ValidationError(
                f"el archivo excede el tamaño máximo de 10MB ({size} bytes)",
                fields={"file": "file exceeds 10MB limit"},
            )

    def _get_storage_path(self, filename: str) -> str:
        now = datetime.now()
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        relative_path = os.path.join(
            UPLOAD_DIR, str(now.year), f"{now.month:02d}", unique_name
        )
        return relative_path

    def _determine_tipo(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        type_map = {
            ".pdf": "PDF",
            ".docx": "DOCUMENTO",
            ".xlsx": "DOCUMENTO",
            ".png": "IMAGEN",
            ".jpg": "IMAGEN",
            ".jpeg": "IMAGEN",
        }
        return type_map.get(ext, "OTRO")

    def _save_to_disk(self, file: UploadFile, relative_path: str) -> None:
        absolute_path = os.path.abspath(relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        with open(absolute_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    def _save_to_s3(self, file: UploadFile, key: str) -> None:
        s3 = self._get_s3_client()
        file.file.seek(0)
        s3.upload_fileobj(file.file, settings.MINIO_BUCKET, key)

    def _download_from_s3(self, key: str) -> str:
        os.makedirs(DOWNLOAD_TEMP_DIR, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, dir=DOWNLOAD_TEMP_DIR, suffix=os.path.splitext(key)[1]
        )
        try:
            s3 = self._get_s3_client()
            s3.download_fileobj(settings.MINIO_BUCKET, key, tmp)
        except ClientError:
            os.unlink(tmp.name)
            raise EntityNotFoundError("Artefacto (archivo)", key)
        return tmp.name

    def _delete_from_disk(self, relative_path: str) -> None:
        absolute_path = os.path.abspath(relative_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)

    def _delete_from_s3(self, key: str) -> None:
        try:
            s3 = self._get_s3_client()
            s3.delete_object(Bucket=settings.MINIO_BUCKET, Key=key)
        except ClientError:
            pass

    def subir(
        self,
        file: UploadFile,
        usuario_id: str,
        ip: str,
        alerta_id: str = None,
        estudiante_id: str = None,
    ) -> dict:
        self._validate_file(file)

        relative_path = self._get_storage_path(file.filename)

        if self.storage_backend == "s3":
            self._save_to_s3(file, relative_path)
        else:
            self._save_to_disk(file, relative_path)

        # validate student is active if estudiante_id is provided
        if estudiante_id:
            est = self.db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
            if not est:
                raise EntityNotFoundError("Estudiante", estudiante_id)
            if est.estado != EstadoEstudiante.ACTIVO:
                raise ValidationError(f"No se pueden subir artefactos para estudiantes en estado {est.estado.value}")

        artefacto = Artefacto(
            nombre=file.filename,
            tipo=self._determine_tipo(file.filename),
            url=relative_path,
            alerta_id=alerta_id,
            estudiante_id=estudiante_id,
            uploaded_by=usuario_id,
        )
        self.db.add(artefacto)
        self.db.commit()
        self.db.refresh(artefacto)

        AuditService.log_crear(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Artefacto",
            entidad_id=str(artefacto.id),
            datos={"nombre": file.filename, "tipo": artefacto.tipo, "ruta": relative_path},
            ip=ip,
        )

        return {
            "id": str(artefacto.id),
            "nombre": artefacto.nombre,
            "tipo": artefacto.tipo,
            "url": artefacto.url,
            "alerta_id": str(artefacto.alerta_id) if artefacto.alerta_id else None,
            "estudiante_id": str(artefacto.estudiante_id) if artefacto.estudiante_id else None,
            "uploaded_by": str(artefacto.uploaded_by),
            "created_at": artefacto.created_at.isoformat() if artefacto.created_at else None,
        }

    def listar(
        self, alerta_id: str = None, estudiante_id: str = None
    ) -> list[dict]:
        query = self.db.query(Artefacto)

        if alerta_id:
            query = query.filter(Artefacto.alerta_id == alerta_id)
        if estudiante_id:
            query = query.filter(Artefacto.estudiante_id == estudiante_id)

        query = query.order_by(Artefacto.created_at.desc())
        artefactos = query.all()

        return [
            {
                "id": str(a.id),
                "nombre": a.nombre,
                "tipo": a.tipo,
                "url": a.url,
                "alerta_id": str(a.alerta_id) if a.alerta_id else None,
                "estudiante_id": str(a.estudiante_id) if a.estudiante_id else None,
                "uploaded_by": str(a.uploaded_by),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in artefactos
        ]

    def obtener(self, artefacto_id: str) -> dict:
        artefacto = (
            self.db.query(Artefacto).filter(Artefacto.id == artefacto_id).first()
        )
        if not artefacto:
            raise EntityNotFoundError("Artefacto", artefacto_id)

        return {
            "id": str(artefacto.id),
            "nombre": artefacto.nombre,
            "tipo": artefacto.tipo,
            "url": artefacto.url,
            "alerta_id": str(artefacto.alerta_id) if artefacto.alerta_id else None,
            "estudiante_id": str(artefacto.estudiante_id) if artefacto.estudiante_id else None,
            "uploaded_by": str(artefacto.uploaded_by),
            "created_at": artefacto.created_at.isoformat() if artefacto.created_at else None,
        }

    def descargar(self, artefacto_id: str) -> str:
        artefacto = (
            self.db.query(Artefacto).filter(Artefacto.id == artefacto_id).first()
        )
        if not artefacto:
            raise EntityNotFoundError("Artefacto", artefacto_id)

        if self.storage_backend == "s3":
            return self._download_from_s3(artefacto.url)

        absolute_path = os.path.abspath(artefacto.url)
        if not os.path.exists(absolute_path):
            raise EntityNotFoundError("Artefacto (archivo)", artefacto_id)

        return absolute_path

    def eliminar(self, artefacto_id: str, usuario_id: str, ip: str) -> None:
        artefacto = (
            self.db.query(Artefacto).filter(Artefacto.id == artefacto_id).first()
        )
        if not artefacto:
            raise EntityNotFoundError("Artefacto", artefacto_id)

        if self.storage_backend == "s3":
            self._delete_from_s3(artefacto.url)
        else:
            self._delete_from_disk(artefacto.url)

        AuditService.log_eliminar(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Artefacto",
            entidad_id=str(artefacto.id),
            datos_eliminados={"nombre": artefacto.nombre, "tipo": artefacto.tipo, "ruta": artefacto.url},
            ip=ip,
        )

        self.db.delete(artefacto)
        self.db.commit()
