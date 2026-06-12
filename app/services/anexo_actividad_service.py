"""Service para Anexos de Actividades Institucionales"""
import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional

import filetype
from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.exceptions import EntityNotFoundError, ValidationError
from app.models.anexo_actividad import AnexoActividad
from app.utils.audit import AuditService


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}

_EXT_TO_MIMES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}
MAX_FILE_SIZE = 10 * 1024 * 1024
UPLOAD_DIR = "uploads/anexos_actividades"


class AnexoActividadService:
    def __init__(self, db: Session):
        self.db = db

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

        header = file.file.read(261)
        file.file.seek(0)
        detected = filetype.guess(header)
        detected_mime = detected.mime if detected else None
        allowed_mimes = _EXT_TO_MIMES.get(ext, set())
        if allowed_mimes and detected_mime not in allowed_mimes:
            raise ValidationError(
                f"el contenido del archivo no coincide con la extensión '{ext}'",
                fields={"file": f"magic bytes mismatch: detected {detected_mime}"},
            )

    def _get_storage_path(self, filename: str) -> str:
        now = datetime.now()
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return os.path.join(UPLOAD_DIR, str(now.year), f"{now.month:02d}", unique_name)

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

    def _count_anexos(self, actividad_id: str) -> int:
        return self.db.query(AnexoActividad).filter(
            AnexoActividad.actividad_id == actividad_id
        ).count()

    def subir(self, actividad_id: str, file: UploadFile, usuario_id: str, ip: str) -> dict:
        if self._count_anexos(actividad_id) >= 5:
            raise ValidationError("máximo 5 archivos por actividad")

        self._validate_file(file)

        relative_path = self._get_storage_path(file.filename)
        absolute_path = os.path.join(settings.UPLOAD_BASE_PATH, relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        with open(absolute_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        anexo = AnexoActividad(
            actividad_id=actividad_id,
            nombre=file.filename,
            tipo=self._determine_tipo(file.filename),
            url=relative_path,
            uploaded_by=usuario_id,
        )
        self.db.add(anexo)
        self.db.flush()
        self.db.refresh(anexo)

        AuditService.log_crear(
            db=self.db,
            usuario_id=usuario_id,
            entidad="AnexoActividad",
            entidad_id=str(anexo.id),
            datos={"nombre": file.filename, "tipo": anexo.tipo, "actividad_id": actividad_id},
            ip=ip,
        )
        self.db.commit()

        return {
            "id": str(anexo.id),
            "actividad_id": str(anexo.actividad_id),
            "nombre": anexo.nombre,
            "tipo": anexo.tipo,
            "url": anexo.url,
            "uploaded_by": str(anexo.uploaded_by),
            "created_at": anexo.created_at.isoformat() if anexo.created_at else None,
        }

    def listar_por_actividad(self, actividad_id: str) -> List[dict]:
        anexos = self.db.query(AnexoActividad).filter(
            AnexoActividad.actividad_id == actividad_id
        ).order_by(desc(AnexoActividad.created_at)).all()

        return [
            {
                "id": str(a.id),
                "actividad_id": str(a.actividad_id),
                "nombre": a.nombre,
                "tipo": a.tipo,
                "url": a.url,
                "uploaded_by": str(a.uploaded_by),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in anexos
        ]

    def obtener(self, anexo_id: str) -> dict:
        anexo = self.db.query(AnexoActividad).filter(
            AnexoActividad.id == anexo_id
        ).first()
        if not anexo:
            raise EntityNotFoundError("AnexoActividad", anexo_id)

        return {
            "id": str(anexo.id),
            "actividad_id": str(anexo.actividad_id),
            "nombre": anexo.nombre,
            "tipo": anexo.tipo,
            "url": anexo.url,
            "uploaded_by": str(anexo.uploaded_by),
            "created_at": anexo.created_at.isoformat() if anexo.created_at else None,
        }

    def descargar(self, anexo_id: str) -> str:
        anexo = self.db.query(AnexoActividad).filter(
            AnexoActividad.id == anexo_id
        ).first()
        if not anexo:
            raise EntityNotFoundError("AnexoActividad", anexo_id)

        absolute_path = os.path.join(settings.UPLOAD_BASE_PATH, anexo.url)
        if not os.path.exists(absolute_path):
            raise EntityNotFoundError("AnexoActividad (archivo)", anexo_id)

        return absolute_path

    def eliminar(self, anexo_id: str, usuario_id: str, ip: str) -> None:
        anexo = self.db.query(AnexoActividad).filter(
            AnexoActividad.id == anexo_id
        ).first()
        if not anexo:
            raise EntityNotFoundError("AnexoActividad", anexo_id)

        absolute_path = os.path.join(settings.UPLOAD_BASE_PATH, anexo.url)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)

        AuditService.log_eliminar(
            db=self.db,
            usuario_id=usuario_id,
            entidad="AnexoActividad",
            entidad_id=str(anexo.id),
            datos_eliminados={"nombre": anexo.nombre, "tipo": anexo.tipo, "actividad_id": str(anexo.actividad_id)},
            ip=ip,
        )
        self.db.delete(anexo)
        self.db.commit()
