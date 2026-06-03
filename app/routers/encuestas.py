"""Encuestas (surveys) — CRUD, publishing lifecycle, public responses, and results."""
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
    ProcesarVencimientosResponse,
)
from app.services.encuesta_service import EncuestaService
from app.services.encuesta_publica_service import EncuestaPublicaService

router = APIRouter(prefix="/api/encuestas", tags=["encuestas"])
limiter = Limiter(key_func=get_remote_address)


# ── public endpoints (no auth) ──────────────────────────────────────────────

@router.get("/publicas", summary="Listar encuestas publicadas",
    description="Retorna todas las encuestas en estado PUBLICADA. No requiere autenticación.")
async def list_encuestas_publicas(
    request: Request, db: Session = Depends(get_db),
):
    service = EncuestaPublicaService(db)
    return {"encuestas": service.listar_publicas()}


@router.get("/{encuesta_id}/info-publica", response_model=InfoPublicaResponse,
    summary="Obtener información pública de una encuesta",
    description="Retorna título, descripción y preguntas de una encuesta PUBLICADA. "
                "No requiere autenticación. Rate limit: 30 peticiones/minuto.")
@limiter.limit("30/minute")
async def get_info_publica(
    encuesta_id: str, request: Request, db: Session = Depends(get_db),
):
    service = EncuestaPublicaService(db)
    return service.obtener_info_publica(encuesta_id)


@router.post("/{encuesta_id}/verificar-estudiante", response_model=VerificarEstudianteResponse,
    summary="Verificar estudiante por documento",
    description="Busca un estudiante por número de documento (hash SHA-256 indexado) y verifica "
                "si puede responder la encuesta. Si el estudiante es válido, retorna las preguntas "
                "con valores pre-llenados desde la base de datos (email/telefono enmascarados). "
                "No requiere autenticación. Rate limit: 10 peticiones/minuto.",
    responses={
        200: {"description": "Estudiante verificado (puede o no responder)"},
        400: {"description": "Encuesta no disponible (no está PUBLICADA)"},
    })
@limiter.limit("10/minute")
async def verificar_estudiante(
    encuesta_id: str, body: VerificarEstudianteRequest,
    request: Request, db: Session = Depends(get_db),
):
    service = EncuestaPublicaService(db)
    result = service.verificar_estudiante(encuesta_id, body.documento)
    return VerificarEstudianteResponse(**result)


@router.post("/{encuesta_id}/responder-publico", status_code=status.HTTP_201_CREATED,
    summary="Responder encuesta como estudiante público",
    description="Envía las respuestas de una encuesta como estudiante sin autenticación. "
                "Verifica el documento, valida los campos mapeados (estrato, género, email, etc.) "
                "ANTES de guardar, y actualiza los datos del estudiante directamente. "
                "Si la validación falla, no se guarda nada y el estudiante puede reintentar. "
                "Rate limit: 5 peticiones/minuto.",
    responses={
        201: {"description": "Respuesta registrada y datos del estudiante actualizados"},
        400: {"description": "Datos inválidos o documento no verificado"},
        409: {"description": "El estudiante ya respondió esta encuesta"},
    })
@limiter.limit("5/minute")
async def responder_publico(
    encuesta_id: str, body: ResponderEncuestaPublica,
    request: Request, db: Session = Depends(get_db),
):
    service = EncuestaPublicaService(db)
    return service.responder_publico(encuesta_id, body.documento, body.respuestas)


@router.post("/plantilla-datos", response_model=EncuestaResponse, status_code=status.HTTP_201_CREATED,
    summary="Crear plantilla de actualización de datos",
    description="Crea una encuesta preconfigurada en estado BORRADOR con 8 preguntas mapeadas "
                "a campos del estudiante: estrato, género, procedencia, ingreso_familiar, email, "
                "teléfono, programa (informativo) y semestre (informativo). "
                "Requiere autenticación de administrador.")
async def crear_encuesta_plantilla_datos(
    request: Request, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaPublicaService(db)
    return service.crear_plantilla_datos(str(current_user.id))


# ── admin endpoints (auth required) ─────────────────────────────────────────

@router.get("", response_model=EncuestaListResponse,
    summary="Listar todas las encuestas",
    description="Retorna encuestas paginadas con filtro opcional por estado. "
                "Requiere autenticación.")
async def list_encuestas(
    request: Request, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Registros por página"),
    estado: str = Query(None, description="Filtrar por estado: BORRADOR, PUBLICADA, CERRADA"),
):
    service = EncuestaService(db)
    resultados, total = service.listar(pagina, por_pagina, estado)
    return EncuestaListResponse(total=total, pagina=pagina, por_pagina=por_pagina, encuestas=resultados)


@router.post("", response_model=EncuestaResponse, status_code=status.HTTP_201_CREATED,
    summary="Crear nueva encuesta",
    description="Crea una encuesta en estado BORRADOR. Las preguntas soportan tipos: "
                "opcion_multiple, texto_libre, escala_likert y ABIERTA. "
                "Requiere permiso 'crear_encuesta'.")
async def create_encuesta(
    encuesta_data: EncuestaCreate, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("crear_encuesta")),
):
    service = EncuestaService(db)
    data = encuesta_data.model_dump()
    data["preguntas"] = [p.model_dump() for p in encuesta_data.preguntas]
    return service.crear(data, str(current_user.id))


@router.get("/{encuesta_id}", response_model=EncuestaResponse,
    summary="Obtener encuesta por ID",
    description="Retorna los detalles completos de una encuesta. Requiere autenticación.")
async def get_encuesta(
    encuesta_id: str, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaService(db)
    return service.obtener(encuesta_id)


@router.put("/{encuesta_id}", response_model=EncuestaResponse,
    summary="Actualizar encuesta",
    description="Modifica título, descripción, preguntas, periodo y fecha_fin de una encuesta. "
                "Solo permitido en estado BORRADOR (título/descripción/preguntas) o PUBLICADA (fecha_fin). "
                "Requiere autenticación.")
async def update_encuesta(
    encuesta_id: str, encuesta_data: EncuestaUpdate,
    request: Request, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaService(db)
    data = encuesta_data.model_dump(exclude_unset=True)
    if "preguntas" in data and data["preguntas"] is not None:
        data["preguntas"] = [p.model_dump() for p in encuesta_data.preguntas]
    return service.actualizar(encuesta_id, data, str(current_user.id))


@router.delete("/{encuesta_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar encuesta",
    description="Elimina una encuesta y todas sus respuestas asociadas (cascade delete). "
                "Requiere autenticación.",
    responses={204: {"description": "Encuesta eliminada exitosamente"}})
async def delete_encuesta(
    encuesta_id: str, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaService(db)
    service.eliminar(encuesta_id, str(current_user.id))
    return None


@router.post("/{encuesta_id}/publicar", response_model=EncuestaResponse,
    summary="Publicar encuesta",
    description="Transiciona una encuesta de BORRADOR a PUBLICADA. La encuesta debe tener "
                "al menos una pregunta. Al publicar se registra la fecha_inicio. "
                "Requiere autenticación.",
    responses={
        200: {"description": "Encuesta publicada"},
        400: {"description": "La encuesta no está en BORRADOR o no tiene preguntas"},
    })
async def publicar_encuesta(
    encuesta_id: str, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaService(db)
    return service.publicar(encuesta_id, str(current_user.id))


@router.post("/{encuesta_id}/cerrar", response_model=EncuestaResponse,
    summary="Cerrar encuesta manualmente",
    description="Transiciona una encuesta de PUBLICADA a CERRADA. Registra la fecha_fin actual. "
                "Requiere autenticación.",
    responses={400: {"description": "La encuesta no está en estado PUBLICADA"}})
async def cerrar_encuesta(
    encuesta_id: str, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaService(db)
    return service.cerrar(encuesta_id, str(current_user.id))


@router.post("/{encuesta_id}/duplicar", response_model=EncuestaResponse,
    summary="Duplicar encuesta",
    description="Clona una encuesta PUBLICADA o CERRADA como nuevo BORRADOR. "
                "Copia título (+ 'copia'), descripción y preguntas. No copia respuestas. "
                "Requiere autenticación.")
async def duplicar_encuesta(
    encuesta_id: str, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaService(db)
    return service.duplicar(encuesta_id, str(current_user.id))


@router.post("/{encuesta_id}/respuestas",
    summary="Registrar respuesta (admin)",
    description="Registra una respuesta a una encuesta PUBLICADA desde el panel admin. "
                "Requiere permiso 'responder_encuesta'. Para respuestas públicas usar "
                "POST /{encuesta_id}/responder-publico.")
async def registrar_respuesta(
    encuesta_id: str, respuesta_data: RespuestaCreate,
    request: Request, db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("responder_encuesta")),
):
    service = EncuestaService(db)
    return service.registrar_respuesta(encuesta_id, str(current_user.id), respuesta_data.respuestas)


@router.get("/{encuesta_id}/resultados", response_model=EncuestaResultados,
    summary="Obtener resultados agregados",
    description="Retorna resultados agregados de una encuesta: distribución de opciones múltiples, "
                "promedio de escalas Likert, lista de respuestas de texto libre. "
                "Requiere permiso 'ver_respuestas_encuesta'.")
async def get_resultados(
    encuesta_id: str, request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_respuestas_encuesta")),
):
    service = EncuestaService(db)
    return service.obtener_resultados(encuesta_id)


@router.post("/procesar-vencimientos", response_model=ProcesarVencimientosResponse,
    summary="Procesar encuestas vencidas",
    description="Cierra automáticamente todas las encuestas PUBLICADA cuya fecha_fin ya pasó. "
                "Diseñado para ejecutarse periódicamente desde el botón 'Verificar estados' "
                "en el panel admin. Retorna el conteo de encuestas cerradas. "
                "Requiere autenticación.")
async def procesar_vencimientos(
    request: Request, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EncuestaService(db)
    return service.procesar_vencimientos()
