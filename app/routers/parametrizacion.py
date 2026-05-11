"""router for system parametrization - thin layer delegating to service"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permiso
from app.models.user import User
from app.schemas.parametrizacion import (
    ParametrizacionResponse, ParametrizacionUpdate, ParametrizacionGroupResponse,
)
from app.services.parametrizacion_service import ParametrizacionService

router = APIRouter(prefix="/api/parametrizacion", tags=["parametrizacion"])


@router.get("", response_model=list[ParametrizacionGroupResponse])
async def list_parametrizacion(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_parametrizacion")),
):
    """list all parameters grouped by category"""
    service = ParametrizacionService(db)
    return service.listar()


@router.get("/{param_id}", response_model=ParametrizacionResponse)
async def get_parametrizacion(
    param_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """get a single parameter by id"""
    service = ParametrizacionService(db)
    return service.obtener(param_id)


@router.put("/{param_id}", response_model=ParametrizacionResponse)
async def update_parametrizacion(
    param_id: str,
    data: ParametrizacionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_parametrizacion")),
):
    """update a parameter value"""
    service = ParametrizacionService(db)
    return service.actualizar(
        param_id, data.valor, str(current_user.id), request.client.host
    )
