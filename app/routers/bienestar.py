"""Router for Bienestar TCBU endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permiso
from app.models.user import User
from app.services.bienestar_service import BienestarService

router = APIRouter(prefix="/api/bienestar", tags=["bienestar"])


@router.get("/tcbu")
async def get_tcbu(
    periodo_inicio: Optional[str] = Query(None),
    periodo_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return TCBU time-series data pivoted for multi-line chart."""
    return BienestarService(db).get_tcbu(periodo_inicio, periodo_fin)


@router.post("/tcbu/carga", status_code=status.HTTP_200_OK)
async def carga_tcbu(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_actividad")),
):
    """Bulk-load TCBU data from a wide-format CSV or XLSX file."""
    return BienestarService(db).carga_csv(
        file=file,
        usuario_id=str(current_user.id),
        ip=request.client.host,
    )


@router.get("/tcbu/plantilla")
async def descargar_plantilla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a CSV template for TCBU bulk upload."""
    csv_bytes = BienestarService(db).generar_plantilla_csv()
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_bienestar_tcbu.csv"},
    )
