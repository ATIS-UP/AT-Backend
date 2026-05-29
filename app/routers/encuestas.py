"""router for survey (encuesta) operations - thin layer delegating to service"""
from fastapi import APIRouter, Depends, Request, Query, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies import get_current_user, require_permiso
from app.models.user import User
from app.schemas.encuesta import (
    EncuestaCreate, EncuestaUpdate, EncuestaResponse,
    EncuestaListResponse, RespuestaCreate, EncuestaResultados,
    VerificarEstudianteRequest, VerificarEstudianteResponse,
    ResponderEncuestaPublica, InfoPublicaResponse,
)
from app.services.encuesta_service import EncuestaService

router = APIRouter(prefix="/api/encuestas", tags=["encuestas"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/publicas")
async def list_encuestas_publicas(
    request: Request,
    db: Session = Depends(get_db),
):
    """list published surveys (no auth required, rate limited)"""
    service = EncuestaService(db)
    return {"encuestas": service.listar_publicas()}


@router.get("/{encuesta_id}/info-publica", response_model=InfoPublicaResponse)
@limiter.limit("30/minute")
async def get_info_publica(
    encuesta_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """get public survey info (no auth required). only for PUBLICADA surveys."""
    service = EncuestaService(db)
    return service.obtener_info_publica(encuesta_id)


@router.post("/{encuesta_id}/verificar-estudiante", response_model=VerificarEstudianteResponse)
@limiter.limit("10/minute")
async def verificar_estudiante(
    encuesta_id: str,
    body: VerificarEstudianteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """verify a student by documento + fecha_nacimiento before answering a survey (no auth required)"""
    service = EncuestaService(db)
    result = service.verificar_estudiante(encuesta_id, body.documento, body.fecha_nacimiento)
    return VerificarEstudianteResponse(**result)


@router.post("/{encuesta_id}/responder-publico", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def responder_publico(
    encuesta_id: str,
    body: ResponderEncuestaPublica,
    request: Request,
    db: Session = Depends(get_db),
):
    """submit survey answers as a public student (no auth required)"""
    service = EncuestaService(db)
    return service.responder_publico(encuesta_id, body.documento, body.fecha_nacimiento, body.respuestas)


@router.get("", response_model=EncuestaListResponse)
async def list_encuestas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    estado: str = Query(None),
):
    """list surveys with pagination and optional estado filter"""
    service = EncuestaService(db)
    resultados, total = service.listar(pagina, por_pagina, estado)
    return EncuestaListResponse(
        total=total, pagina=pagina, por_pagina=por_pagina, encuestas=resultados
    )


@router.post("", response_model=EncuestaResponse, status_code=status.HTTP_201_CREATED)
async def create_encuesta(
    encuesta_data: EncuestaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_encuesta")),
):
    """create a new survey"""
    service = EncuestaService(db)
    data = encuesta_data.model_dump()
    # convert PreguntaEncuesta objects to dicts for service layer
    data["preguntas"] = [p.model_dump() for p in encuesta_data.preguntas]
    return service.crear(data, str(current_user.id))


@router.get("/{encuesta_id}", response_model=EncuestaResponse)
async def get_encuesta(
    encuesta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """get a survey by id"""
    service = EncuestaService(db)
    return service.obtener(encuesta_id)


@router.put("/{encuesta_id}", response_model=EncuestaResponse)
async def update_encuesta(
    encuesta_id: str,
    encuesta_data: EncuestaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """update a survey (only allowed in BORRADOR state)"""
    service = EncuestaService(db)
    data = encuesta_data.model_dump(exclude_unset=True)
    if "preguntas" in data and data["preguntas"] is not None:
        data["preguntas"] = [p.model_dump() for p in encuesta_data.preguntas]
    return service.actualizar(encuesta_id, data, str(current_user.id))


@router.delete("/{encuesta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_encuesta(
    encuesta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """delete a survey and its responses"""
    service = EncuestaService(db)
    service.eliminar(encuesta_id, str(current_user.id))
    return None


@router.post("/{encuesta_id}/publicar", response_model=EncuestaResponse)
async def publicar_encuesta(
    encuesta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """publish a survey (transition from BORRADOR to PUBLICADA)"""
    service = EncuestaService(db)
    return service.publicar(encuesta_id, str(current_user.id))


@router.post("/{encuesta_id}/cerrar", response_model=EncuestaResponse)
async def cerrar_encuesta(
    encuesta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """close a survey (transition from PUBLICADA to CERRADA)"""
    service = EncuestaService(db)
    return service.cerrar(encuesta_id, str(current_user.id))


@router.post("/{encuesta_id}/respuestas")
async def registrar_respuesta(
    encuesta_id: str,
    respuesta_data: RespuestaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("responder_encuesta")),
):
    """register a response to a published survey"""
    service = EncuestaService(db)
    return service.registrar_respuesta(
        encuesta_id, str(current_user.id), respuesta_data.respuestas
    )


@router.get("/{encuesta_id}/resultados", response_model=EncuestaResultados)
async def get_resultados(
    encuesta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_respuestas_encuesta")),
):
    """get aggregated results for a survey"""
    service = EncuestaService(db)
    return service.obtener_resultados(encuesta_id)
