"""Router para Actividades Institucionales"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.schemas.actividad_institucional import (
    ActividadInstitucionalCreate,
    ActividadInstitucionalUpdate,
    ActividadInstitucionalResponse,
    ActividadInstitucionalListResponse,
)
from app.services.actividad_institucional_service import ActividadInstitucionalService

router = APIRouter(prefix="/api/actividades-institucionales", tags=["actividades_institucionales"])


def get_service(db: Session = Depends(get_db)) -> ActividadInstitucionalService:
    return ActividadInstitucionalService(db)


@router.get("", response_model=ActividadInstitucionalListResponse)
async def listar_actividades(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_actividades"))
):
    service = get_service(db)
    actividades, total = service.listar(pagina, por_pagina, estado)
    return {
        "actividades": actividades,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina
    }


@router.get("/{actividad_id}", response_model=ActividadInstitucionalResponse)
async def obtener_actividad(
    actividad_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_actividades"))
):
    service = get_service(db)
    actividad = service.obtener(actividad_id)
    if not actividad:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actividad no encontrada")
    return actividad


@router.post("", response_model=ActividadInstitucionalResponse, status_code=201)
async def crear_actividad(
    data: ActividadInstitucionalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_actividad"))
):
    service = get_service(db)
    return service.crear(data, str(current_user.id))


@router.put("/{actividad_id}", response_model=ActividadInstitucionalResponse)
async def actualizar_actividad(
    actividad_id: str,
    data: ActividadInstitucionalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_actividad"))
):
    service = get_service(db)
    actividad = service.actualizar(actividad_id, data)
    if not actividad:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actividad no encontrada")
    return actividad


@router.delete("/{actividad_id}", status_code=204)
async def eliminar_actividad(
    actividad_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("eliminar_actividad"))
):
    service = get_service(db)
    eliminado = service.eliminar(actividad_id)
    if not eliminado:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actividad no encontrada")
    return None
