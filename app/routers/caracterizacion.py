"""Router for socioeconomic characterization endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.caracterizacion_service import CaracterizacionService

router = APIRouter(prefix="/api/caracterizacion", tags=["caracterizacion"])


@router.get("/socioeconomica")
async def get_socioeconomica(
    periodo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CaracterizacionService(db).socioeconomica(periodo)


@router.get("/procedencia")
async def get_procedencia(
    periodo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CaracterizacionService(db).procedencia(periodo)


@router.get("/genero")
async def get_genero(
    periodo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CaracterizacionService(db).genero(periodo)
