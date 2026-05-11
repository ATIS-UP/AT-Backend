"""router for student operations - thin layer delegating to service"""
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.schemas.estudiante import (
    EstudianteCreate, EstudianteUpdate, EstudianteResponse,
    EstudianteListResponse, HistorialAcademico
)
from app.schemas.common import CargaMasivaResumen
from app.services.estudiante_service import EstudianteService
from app.services.carga_masiva_service import CargaMasivaService

router = APIRouter(prefix="/api/estudiantes", tags=["estudiantes"])


@router.get("", response_model=EstudianteListResponse)
async def list_estudiantes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_estudiantes")),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    buscar: str = Query(None),
    estado: str = Query(None),
    programa: str = Query(None)
):
    """list students with pagination and filters"""
    service = EstudianteService(db)
    resultados, total = service.listar(pagina, por_pagina, buscar, estado, programa)
    return EstudianteListResponse(
        total=total, pagina=pagina, por_pagina=por_pagina, estudiantes=resultados
    )


@router.get("/{estudiante_id}", response_model=EstudianteResponse)
async def get_estudiante(
    estudiante_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_estudiantes"))
):
    """get a student by id"""
    service = EstudianteService(db)
    return service.obtener(estudiante_id)


@router.post("", response_model=EstudianteResponse, status_code=status.HTTP_201_CREATED)
async def create_estudiante(
    estudiante_data: EstudianteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_estudiante"))
):
    """create a new student"""
    service = EstudianteService(db)
    return service.crear(estudiante_data, str(current_user.id), request.client.host)


@router.put("/{estudiante_id}", response_model=EstudianteResponse)
async def update_estudiante(
    estudiante_id: str,
    estudiante_data: EstudianteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_estudiante"))
):
    """update a student"""
    service = EstudianteService(db)
    return service.actualizar(
        estudiante_id, estudiante_data, str(current_user.id), request.client.host
    )


@router.delete("/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_estudiante(
    estudiante_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("eliminar_estudiante"))
):
    """delete a student"""
    service = EstudianteService(db)
    service.eliminar(estudiante_id, str(current_user.id), request.client.host)
    return None


@router.get("/{estudiante_id}/historial", response_model=HistorialAcademico)
async def get_historial(
    estudiante_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_estudiantes"))
):
    """get academic history for a student"""
    service = EstudianteService(db)
    return service.obtener_historial(estudiante_id)


@router.post("/carga-masiva", response_model=CargaMasivaResumen)
async def carga_masiva(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_estudiante")),
):
    """bulk upload students from csv/xlsx file"""
    service = CargaMasivaService(db)
    return service.procesar_archivo(file, str(current_user.id), request.client.host)
