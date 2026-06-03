"""Router for Participacion Estudiantil (#78)."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.participacion_service import ParticipacionService

router = APIRouter(prefix="/api/participacion", tags=["participacion"])


@router.get("/procedencia")
async def get_procedencia(
    periodo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ParticipacionService(db).procedencia(periodo)


@router.get("/genero")
async def get_genero(
    periodo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ParticipacionService(db).genero(periodo)


@router.get("/estrato")
async def get_estrato(
    periodo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ParticipacionService(db).estrato(periodo)
