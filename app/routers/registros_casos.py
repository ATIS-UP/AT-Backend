"""Router para Registros de Casos Especiales"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.schemas.caso_especial import (
    RegistroCasoCreate, RegistroCasoUpdate, RegistroCasoResponse,
    RegistroCasoListResponse, BusquedaEstudianteResponse, HistorialCreate,
    HistorialResponse, HistorialListResponse
)
from app.services.caso_especial_service import CasoEspecialService

router = APIRouter(prefix="/api/registros-casos", tags=["registros_casos"])


def get_service(db: Session = Depends(get_db)) -> CasoEspecialService:
    return CasoEspecialService(db)


def get_current_user_from_request(request: Request, db: Session = Depends(get_db)) -> User:
    from app.utils.auth import verify_token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    token = auth_header.replace("Bearer ", "")
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    
    return user


@router.get("/buscar-estudiante")
async def buscar_estudiante(
    q: str = Query(..., min_length=1, description="Texto de búsqueda"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_registros_casos"))
):
    """Buscar estudiantes por documento, nombre, apellido o código"""
    service = get_service(db)
    resultados, total = service.buscar_estudiantes(q, pagina, por_pagina)
    return {
        "resultados": resultados,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina
    }


@router.post("", response_model=RegistroCasoResponse, status_code=status.HTTP_201_CREATED)
async def crear_registro(
    data: RegistroCasoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_registro_caso"))
):
    """Crear un nuevo registro de caso especial"""
    service = get_service(db)
    return service.crear(data, str(current_user.id), current_user.nombre)


@router.get("", response_model=RegistroCasoListResponse)
async def listar_registros(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    estado: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_registros_casos"))
):
    """Listar registros de casos especiales"""
    service = get_service(db)
    registros, total = service.listar(pagina, por_pagina, estado, tipo)
    return RegistroCasoListResponse(
        registros=registros,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina
    )


@router.get("/{registro_id}", response_model=RegistroCasoResponse)
async def obtener_registro(
    registro_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_registros_casos"))
):
    """Obtener un registro de caso especial por ID"""
    service = get_service(db)
    registro = service.obtener(registro_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return registro


@router.put("/{registro_id}", response_model=RegistroCasoResponse)
async def actualizar_registro(
    registro_id: str,
    data: RegistroCasoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_registro_caso"))
):
    """Actualizar un registro de caso especial"""
    service = get_service(db)
    registro = service.actualizar(registro_id, data, str(current_user.id), current_user.nombre)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return registro


@router.delete("/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_registro(
    registro_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("editar_registro_caso"))
):
    """Eliminar un registro de caso especial"""
    service = get_service(db)
    if not service.eliminar(registro_id):
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return None


@router.get("/{registro_id}/historial", response_model=HistorialListResponse)
async def obtener_historial(
    registro_id: str,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_registros_casos"))
):
    """Obtener el historial de un registro"""
    service = get_service(db)
    historiales = service.obtener_historial(registro_id)
    return HistorialListResponse(historiales=historiales, total=len(historiales))


@router.post("/{registro_id}/historial", response_model=RegistroCasoResponse)
async def agregar_historial(
    registro_id: str,
    data: HistorialCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_registro_caso"))
):
    """Agregar una entrada al historial de un registro"""
    service = get_service(db)
    registro = service.agregar_historial(
        registro_id, data.accion, data.observaciones,
        str(current_user.id), current_user.nombre
    )
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return registro