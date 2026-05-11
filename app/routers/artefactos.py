"""router for artifact (artefacto) operations - thin layer delegating to service"""
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permiso
from app.models.user import User
from app.schemas.artefacto import ArtefactoResponse, ArtefactoListResponse
from app.services.artefacto_service import ArtefactoService

router = APIRouter(prefix="/api/artefactos", tags=["artefactos"])


@router.post("", response_model=ArtefactoResponse, status_code=status.HTTP_201_CREATED)
async def upload_artefacto(
    request: Request,
    file: UploadFile = File(...),
    alerta_id: str = Query(None),
    estudiante_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("subir_artefacto")),
):
    """upload a file artifact"""
    service = ArtefactoService(db)
    return service.subir(
        file=file,
        usuario_id=str(current_user.id),
        ip=request.client.host,
        alerta_id=alerta_id,
        estudiante_id=estudiante_id,
    )


@router.get("", response_model=ArtefactoListResponse)
async def list_artefactos(
    request: Request,
    alerta_id: str = Query(None),
    estudiante_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """list artifacts filtered by alerta_id or estudiante_id"""
    service = ArtefactoService(db)
    artefactos = service.listar(alerta_id=alerta_id, estudiante_id=estudiante_id)
    return ArtefactoListResponse(artefactos=artefactos)


@router.get("/{artefacto_id}", response_model=ArtefactoResponse)
async def get_artefacto(
    artefacto_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """get artifact metadata by id"""
    service = ArtefactoService(db)
    return service.obtener(artefacto_id)


@router.get("/{artefacto_id}/download")
async def download_artefacto(
    artefacto_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """download an artifact file"""
    service = ArtefactoService(db)
    file_path = service.descargar(artefacto_id)
    return FileResponse(path=file_path)


@router.delete("/{artefacto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artefacto(
    artefacto_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("eliminar_artefacto")),
):
    """delete an artifact (file and db record)"""
    service = ArtefactoService(db)
    service.eliminar(artefacto_id, str(current_user.id), request.client.host)
    return None
