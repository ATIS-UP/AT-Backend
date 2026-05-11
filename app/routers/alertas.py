"""router for alert operations - thin layer delegating to service"""
from typing import List
from fastapi import APIRouter, Depends, Request, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.schemas.alerta import (
    AlertaCreate, AlertaUpdate, AlertaResponse, AlertaListResponse,
    AlertaEstadoUpdate, AlertasStats, ActividadCreate, ActividadResponse
)
from app.services.alerta_service import AlertaService

router = APIRouter(prefix="/api/alertas", tags=["alertas"])


@router.get("", response_model=AlertaListResponse)
async def list_alertas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_alertas")),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    nivel_riesgo: str = Query(None),
    estado_seguimiento: str = Query(None),
    periodo: str = Query(None)
):
    """list alerts with filters"""
    service = AlertaService(db)
    resultados, total = service.listar(
        pagina, por_pagina, nivel_riesgo, estado_seguimiento, periodo
    )
    return AlertaListResponse(
        total=total, pagina=pagina, por_pagina=por_pagina, alertas=resultados
    )


@router.get("/stats", response_model=AlertasStats)
async def get_alertas_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_alertas"))
):
    """get alert statistics"""
    service = AlertaService(db)
    return service.get_stats()


@router.get("/{alerta_id}", response_model=AlertaResponse)
async def get_alerta(
    alerta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_alertas"))
):
    """get an alert by id"""
    service = AlertaService(db)
    return service.obtener(alerta_id)


@router.post("", response_model=AlertaResponse, status_code=status.HTTP_201_CREATED)
async def create_alerta(
    alerta_data: AlertaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_alerta"))
):
    """create a new alert"""
    service = AlertaService(db)
    return service.crear(alerta_data, str(current_user.id), request.client.host)


@router.put("/{alerta_id}", response_model=AlertaResponse)
async def update_alerta(
    alerta_id: str,
    alerta_data: AlertaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_alerta"))
):
    """update an alert"""
    service = AlertaService(db)
    return service.actualizar(
        alerta_id, alerta_data, str(current_user.id), request.client.host
    )


@router.put("/{alerta_id}/estado", response_model=AlertaResponse)
async def update_estado(
    alerta_id: str,
    estado_data: AlertaEstadoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("cambiar_estado_alerta"))
):
    """change follow-up state of an alert"""
    service = AlertaService(db)
    return service.cambiar_estado(
        alerta_id, estado_data.estado_seguimiento, str(current_user.id), request.client.host
    )


@router.delete("/{alerta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alerta(
    alerta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("eliminar_alerta"))
):
    """delete an alert"""
    service = AlertaService(db)
    service.eliminar(alerta_id, str(current_user.id), request.client.host)
    return None


# activity endpoints
@router.get("/{alerta_id}/actividades", response_model=List[ActividadResponse])
async def list_actividades(
    alerta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_actividades"))
):
    """list activities for an alert"""
    service = AlertaService(db)
    return service.listar_actividades(alerta_id)


@router.post("/{alerta_id}/actividades", response_model=ActividadResponse, status_code=status.HTTP_201_CREATED)
async def create_actividad(
    alerta_id: str,
    actividad_data: ActividadCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_actividad"))
):
    """create an activity for an alert"""
    service = AlertaService(db)
    return service.registrar_actividad(
        alerta_id, actividad_data, str(current_user.id)
    )
