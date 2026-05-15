"""Router para Anexos de Actividades Institucionales"""
from fastapi import APIRouter, Depends, File, UploadFile, Query, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.services.anexo_actividad_service import AnexoActividadService

router = APIRouter(prefix="/api/actividades", tags=["anexos_actividades"])


def get_service(db: Session = Depends(get_db)) -> AnexoActividadService:
    return AnexoActividadService(db)


@router.post("/{actividad_id}/anexos", status_code=201)
async def subir_anexo(
    actividad_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_permiso("crear_actividad")),
):
    service = get_service(db)
    ip = request.client.host if request else "0.0.0.0"
    return service.subir(actividad_id, file, str(current_user.id), ip)


@router.get("/{actividad_id}/anexos")
async def listar_anexos(
    actividad_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_actividades")),
):
    service = get_service(db)
    anexos = service.listar_por_actividad(actividad_id)
    return {"anexos": anexos, "total": len(anexos)}


@router.get("/anexos/{anexo_id}/download")
async def descargar_anexo(
    anexo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_actividades")),
):
    service = get_service(db)
    file_path = service.descargar(anexo_id)
    anexo = service.obtener(anexo_id)
    return FileResponse(
        path=file_path,
        filename=anexo["nombre"],
        media_type="application/octet-stream",
    )


@router.delete("/anexos/{anexo_id}", status_code=204)
async def eliminar_anexo(
    anexo_id: str,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_permiso("editar_actividad")),
):
    service = get_service(db)
    ip = request.client.host if request else "0.0.0.0"
    service.eliminar(anexo_id, str(current_user.id), ip)
    return None
