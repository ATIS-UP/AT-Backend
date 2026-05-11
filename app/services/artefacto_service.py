"""service for managing file artifacts (upload, list, download, delete)."""

import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.exceptions import EntityNotFoundError, ValidationError
from app.models.alerta import Artefacto
from app.utils.audit import AuditService


# allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}

# max file size: 10mb
MAX_FILE_SIZE = 10 * 1024 * 1024

# base upload directory
UPLOAD_DIR = "uploads"


class ArtefactoService:
    """handles file artifact operations: upload, list, download, delete."""

    def __init__(self, db: Session):
        self.db = db

    def _validate_file(self, file: UploadFile) -> None:
        """validate file extension and size."""
        if not file.filename:
            raise ValidationError("el nombre del archivo es requerido")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"tipo de archivo no permitido: {ext}. permitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                fields={"file": f"extension {ext} not allowed"},
            )

        # read content to check size
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        if size > MAX_FILE_SIZE:
            raise ValidationError(
                f"el archivo excede el tamaño máximo de 10MB ({size} bytes)",
                fields={"file": "file exceeds 10MB limit"},
            )

    def _get_storage_path(self, filename: str) -> str:
        """generate organized storage path: uploads/{YYYY}/{MM}/{filename_uuid.ext}"""
        now = datetime.now()
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        relative_path = os.path.join(
            UPLOAD_DIR, str(now.year), f"{now.month:02d}", unique_name
        )
        return relative_path

    def _determine_tipo(self, filename: str) -> str:
        """determine file type category from extension."""
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

    def subir(
        self,
        file: UploadFile,
        usuario_id: str,
        ip: str,
        alerta_id: str = None,
        estudiante_id: str = None,
    ) -> dict:
        """upload a file, validate, save to disk, create db record, audit log."""
        self._validate_file(file)

        relative_path = self._get_storage_path(file.filename)
        absolute_path = os.path.abspath(relative_path)

        # ensure directory exists
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # save file to disk
        with open(absolute_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # create db record
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

        # audit log
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
        """list artifacts filtered by alerta or estudiante."""
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
        """get artifact metadata by id, raises EntityNotFoundError if not found."""
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
        """return absolute file path for download, raises EntityNotFoundError if not found."""
        artefacto = (
            self.db.query(Artefacto).filter(Artefacto.id == artefacto_id).first()
        )
        if not artefacto:
            raise EntityNotFoundError("Artefacto", artefacto_id)

        absolute_path = os.path.abspath(artefacto.url)
        if not os.path.exists(absolute_path):
            raise EntityNotFoundError("Artefacto (archivo)", artefacto_id)

        return absolute_path

    def eliminar(self, artefacto_id: str, usuario_id: str, ip: str) -> None:
        """delete file from disk and db record, audit log."""
        artefacto = (
            self.db.query(Artefacto).filter(Artefacto.id == artefacto_id).first()
        )
        if not artefacto:
            raise EntityNotFoundError("Artefacto", artefacto_id)

        # remove file from disk if it exists
        absolute_path = os.path.abspath(artefacto.url)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)

        # audit log before deletion
        AuditService.log_eliminar(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Artefacto",
            entidad_id=str(artefacto.id),
            datos_eliminados={"nombre": artefacto.nombre, "tipo": artefacto.tipo, "ruta": artefacto.url},
            ip=ip,
        )

        # delete db record
        self.db.delete(artefacto)
        self.db.commit()
