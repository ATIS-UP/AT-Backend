"""Router for Monitoreo Academico (#64)."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.monitoreo_service import MonitoreoService

router = APIRouter(prefix="/api/monitoreo", tags=["monitoreo"])


@router.get("/materias-dificultad")
async def get_materias_dificultad(
    periodo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MonitoreoService(db).materias_dificultad(periodo)
