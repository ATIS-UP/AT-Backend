"""Router para Novedades de Casos Especiales"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.schemas.novedad_caso import NovedadCasoCreate, NovedadCasoUpdate, NovedadCasoResponse
from app.services.novedad_caso_service import NovedadCasoService

router = APIRouter(prefix="/api/novedades-casos", tags=["novedades_casos"])


def get_service(db: Session = Depends(get_db)) -> NovedadCasoService:
    return NovedadCasoService(db)


@router.get("", response_model=list[NovedadCasoResponse])
async def listar_novedades(
    tipo_caso: Optional[str] = Query(None),
    solo_activos: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_registros_casos")),
):
    service = get_service(db)
    return service.listar(tipo_caso, solo_activos)


@router.post("", response_model=NovedadCasoResponse, status_code=status.HTTP_201_CREATED)
async def crear_novedad(
    data: NovedadCasoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_registro_caso")),
):
    service = get_service(db)
    return service.crear(data)


@router.put("/{novedad_id}", response_model=NovedadCasoResponse)
async def actualizar_novedad(
    novedad_id: str,
    data: NovedadCasoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_registro_caso")),
):
    service = get_service(db)
    result = service.actualizar(novedad_id, data)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Novedad no encontrada")
    return result


@router.delete("/{novedad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_novedad(
    novedad_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_registro_caso")),
):
    service = get_service(db)
    if not service.eliminar(novedad_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Novedad no encontrada")
    return None
