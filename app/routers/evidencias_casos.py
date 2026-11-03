
"""API privada de evidencias fotográficas de casos especiales."""

import uuid
from pathlib import Path

from fastapi import (
    APIRouter, Depends, File, HTTPException,
    UploadFile, status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.models.caso_especial import RegistroCasoEspecial
from app.models.evidencia_caso import EvidenciaCaso
from app.utils import storage


router = APIRouter(
    prefix="/api/registros-casos",
    tags=["evidencias_casos"],
)

MAX_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 10

# evidencia.ruta es relativa a este prefijo ("<registro_id>/<archivo>").
PREFIJO_STORAGE = "uploads/evidencias_casos"


def parse_id(value: str):
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Identificador inválido",
        )


def verificar_registro(db: Session, registro_id: str):
    registro = db.get(
        RegistroCasoEspecial,
        parse_id(registro_id),
    )

    if registro is None:
        raise HTTPException(
            status_code=404,
            detail="Caso especial no encontrado",
        )

    return registro


def respuesta(evidencia: EvidenciaCaso):
    return {
        "id": str(evidencia.id),
        "registro_id": str(evidencia.registro_id),
        "nombre": evidencia.nombre,
        "tipo": evidencia.tipo,
        "created_at": (
            evidencia.created_at.isoformat()
            if evidencia.created_at else None
        ),
    }


def obtener_evidencia(db: Session, evidencia_id: str):
    evidencia = db.get(
        EvidenciaCaso,
        parse_id(evidencia_id),
    )

    if evidencia is None:
        raise HTTPException(
            status_code=404,
            detail="Fotografía no encontrada",
        )

    return evidencia


def clave_storage(ruta: str) -> str:
    return f"{PREFIJO_STORAGE}/{ruta}"


@router.get("/{registro_id}/evidencias")
def listar_evidencias(
    registro_id: str,
    db: Session = Depends(get_db),
    usuario: User = Depends(
        require_permiso("ver_registros_casos")
    ),
):
    verificar_registro(db, registro_id)

    evidencias = (
        db.query(EvidenciaCaso)
        .filter(
            EvidenciaCaso.registro_id == parse_id(registro_id)
        )
        .order_by(EvidenciaCaso.created_at.desc())
        .all()
    )

    return {
        "evidencias": [respuesta(e) for e in evidencias],
        "total": len(evidencias),
    }


@router.post(
    "/{registro_id}/evidencias",
    status_code=status.HTTP_201_CREATED,
)
async def subir_evidencia(
    registro_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: User = Depends(
        require_permiso("crear_registro_caso")
    ),
):
    verificar_registro(db, registro_id)

    cantidad = (
        db.query(EvidenciaCaso)
        .filter(
            EvidenciaCaso.registro_id == parse_id(registro_id)
        )
        .count()
    )

    if cantidad >= MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail="Máximo 10 fotografías por caso",
        )

    nombre = Path(file.filename or "").name[:255]

    if not nombre:
        raise HTTPException(
            status_code=400,
            detail="El archivo necesita un nombre",
        )

    extension = Path(nombre).suffix.lower()

    if extension not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten imágenes JPG y PNG",
        )

    contenido = await file.read(MAX_BYTES + 1)

    if len(contenido) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="La imagen supera los 5 MB",
        )

    es_png = (
        extension == ".png"
        and contenido.startswith(b"\x89PNG\r\n\x1a\n")
    )
    es_jpeg = (
        extension in {".jpg", ".jpeg"}
        and contenido.startswith(b"\xff\xd8\xff")
    )

    if not (es_png or es_jpeg):
        raise HTTPException(
            status_code=400,
            detail="El contenido no corresponde a una imagen válida",
        )

    identificador = uuid.uuid4()
    tipo = "image/png" if es_png else "image/jpeg"
    nombre_interno = f"{identificador.hex}{extension}"

    ruta = f"{parse_id(registro_id)}/{nombre_interno}"
    clave = clave_storage(ruta)

    try:
        storage.guardar(clave, contenido, tipo)

        evidencia = EvidenciaCaso(
            id=identificador,
            registro_id=parse_id(registro_id),
            nombre=nombre,
            ruta=ruta,
            tipo=tipo,
            uploaded_by=usuario.id,
        )

        db.add(evidencia)
        db.commit()
        db.refresh(evidencia)

        return respuesta(evidencia)

    except Exception:
        db.rollback()
        storage.eliminar(clave)
        raise


@router.get("/evidencias/{evidencia_id}/archivo")
def obtener_archivo(
    evidencia_id: str,
    db: Session = Depends(get_db),
    usuario: User = Depends(
        require_permiso("ver_registros_casos")
    ),
):
    evidencia = obtener_evidencia(db, evidencia_id)
    contenido = storage.leer(clave_storage(evidencia.ruta))

    if contenido is None:
        raise HTTPException(
            status_code=404,
            detail="Archivo no disponible",
        )

    return storage.respuesta_archivo(
        contenido,
        evidencia.nombre,
        evidencia.tipo,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete(
    "/evidencias/{evidencia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_evidencia(
    evidencia_id: str,
    db: Session = Depends(get_db),
    usuario: User = Depends(
        require_permiso("editar_registro_caso")
    ),
):
    evidencia = obtener_evidencia(db, evidencia_id)
    clave = clave_storage(evidencia.ruta)

    db.delete(evidencia)
    db.commit()

    storage.eliminar(clave)

    return None
