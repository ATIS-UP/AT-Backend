"""Router de alertas"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.alerta import Alerta, Actividad
from app.models.estudiante import Estudiante
from app.schemas.alerta import (
    AlertaCreate, AlertaUpdate, AlertaResponse, AlertaListResponse,
    AlertaEstadoUpdate, AlertasStats, ActividadCreate, ActividadResponse
)
from app.utils.auth import verify_token
from app.utils.security import encrypt_data, decrypt_data
from app.utils.permisos import PermisoService
from app.utils.audit import AuditService

router = APIRouter(prefix="/api/alertas", tags=["alertas"])
security = HTTPBearer()


def get_current_user_with_permiso(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")
    return user


@router.get("", response_model=AlertaListResponse)
async def list_alertas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    nivel_riesgo: str = Query(None),
    estado_seguimiento: str = Query(None),
    periodo: str = Query(None)
):
    """Listar alertas con filtros"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_alertas"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    query = db.query(Alerta)

    if nivel_riesgo:
        query = query.filter(Alerta.nivel_riesgo == nivel_riesgo)
    if estado_seguimiento:
        query = query.filter(Alerta.estado_seguimiento == estado_seguimiento)
    if periodo:
        query = query.filter(Alerta.periodo == periodo)

    total = query.count()
    alertas = query.order_by(Alerta.created_at.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    resultados = []
    for a in alertas:
        resultados.append(AlertaResponse(
            id=str(a.id),
            estudiante_id=str(a.estudiante_id),
            materia_id=str(a.materia_id) if a.materia_id else None,
            nivel_riesgo=a.nivel_riesgo.value,
            estado_seguimiento=a.estado_seguimiento.value,
            descripcion=a.descripcion,
            periodo=a.periodo,
            promedio_anterior=float(decrypt_data(str(a.promedio_anterior))) if a.promedio_anterior else None,
            promedio_actual=float(decrypt_data(str(a.promedio_actual))) if a.promedio_actual else None,
            promedio_proyeccion=float(decrypt_data(str(a.promedio_proyeccion))) if a.promedio_proyeccion else None,
            docentes_notificados=a.docentes_notificados or [],
            created_at=a.created_at,
            updated_at=a.updated_at
        ))

    return AlertaListResponse(total=total, pagina=pagina, por_pagina=por_pagina, alertas=resultados)


@router.get("/stats", response_model=AlertasStats)
async def get_alertas_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener estadísticas de alertas"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_alertas"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    from app.models.alerta import NivelRiesgo, EstadoSeguimiento

    total = db.query(Alerta).count()
    critico = db.query(Alerta).filter(Alerta.nivel_riesgo == NivelRiesgo.ROJO).count()
    medio = db.query(Alerta).filter(Alerta.nivel_riesgo == NivelRiesgo.AMARILLO).count()
    bajo = db.query(Alerta).filter(Alerta.nivel_riesgo == NivelRiesgo.VERDE).count()
    pendientes = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.PENDIENTE).count()
    en_proceso = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.EN_PROCESO).count()
    resueltos = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.RESUELTO).count()

    return AlertasStats(
        total=total, critico=critico, medio=medio, bajo=bajo,
        pendientes=pendientes, en_proceso=en_proceso, resueltos=resueltos
    )


@router.get("/{alerta_id}", response_model=AlertaResponse)
async def get_alerta(
    alerta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener una alerta por ID"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_alertas"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    a = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    return AlertaResponse(
        id=str(a.id),
        estudiante_id=str(a.estudiante_id),
        materia_id=str(a.materia_id) if a.materia_id else None,
        nivel_riesgo=a.nivel_riesgo.value,
        estado_seguimiento=a.estado_seguimiento.value,
        descripcion=a.descripcion,
        periodo=a.periodo,
        promedio_anterior=float(decrypt_data(str(a.promedio_anterior))) if a.promedio_anterior else None,
        promedio_actual=float(decrypt_data(str(a.promedio_actual))) if a.promedio_actual else None,
        promedio_proyeccion=float(decrypt_data(str(a.promedio_proyeccion))) if a.promedio_proyeccion else None,
        docentes_notificados=a.docentes_notificados or [],
        created_at=a.created_at,
        updated_at=a.updated_at
    )


@router.post("", response_model=AlertaResponse, status_code=status.HTTP_201_CREATED)
async def create_alerta(
    alerta_data: AlertaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Crear una nueva alerta"""
    if not PermisoService.tiene_permiso(db, current_user, "crear_alerta"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    # Verificar que el estudiante existe
    est = db.query(Estudiante).filter(Estudiante.id == alerta_data.estudiante_id).first()
    if not est:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado")

    nueva = Alerta(
        estudiante_id=alerta_data.estudiante_id,
        materia_id=alerta_data.materia_id,
        nivel_riesgo=alerta_data.nivel_riesgo,
        descripcion=alerta_data.descripcion,
        periodo=alerta_data.periodo,
        promedio_anterior=encrypt_data(str(alerta_data.promedio_anterior)) if alerta_data.promedio_anterior else None,
        promedio_actual=encrypt_data(str(alerta_data.promedio_actual)) if alerta_data.promedio_actual else None
    )

    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    AuditService.log_crear(db, str(current_user.id), "Alerta", str(nueva.id),
                          {"estudiante_id": str(nueva.estudiante_id), "nivel": nueva.nivel_riesgo.value},
                          request.client.host)

    return AlertaResponse(
        id=str(nueva.id),
        estudiante_id=str(nueva.estudiante_id),
        materia_id=str(nueva.materia_id) if nueva.materia_id else None,
        nivel_riesgo=nueva.nivel_riesgo.value,
        estado_seguimiento=nueva.estado_seguimiento.value,
        descripcion=nueva.descripcion,
        periodo=nueva.periodo,
        promedio_anterior=None,
        promedio_actual=None,
        promedio_proyeccion=None,
        docentes_notificados=[],
        created_at=nueva.created_at,
        updated_at=nueva.updated_at
    )


@router.put("/{alerta_id}", response_model=AlertaResponse)
async def update_alerta(
    alerta_id: str,
    alerta_data: AlertaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Actualizar una alerta"""
    if not PermisoService.tiene_permiso(db, current_user, "editar_alerta"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    a = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    update_data = alerta_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ["promedio_actual", "promedio_proyeccion"]:
            setattr(a, key, encrypt_data(str(value)) if value else None)
        else:
            setattr(a, key, value)

    db.commit()
    db.refresh(a)

    return AlertaResponse(
        id=str(a.id),
        estudiante_id=str(a.estudiante_id),
        materia_id=str(a.materia_id) if a.materia_id else None,
        nivel_riesgo=a.nivel_riesgo.value,
        estado_seguimiento=a.estado_seguimiento.value,
        descripcion=a.descripcion,
        periodo=a.periodo,
        promedio_anterior=float(decrypt_data(str(a.promedio_anterior))) if a.promedio_anterior else None,
        promedio_actual=float(decrypt_data(str(a.promedio_actual))) if a.promedio_actual else None,
        promedio_proyeccion=float(decrypt_data(str(a.promedio_proyeccion))) if a.promedio_proyeccion else None,
        docentes_notificados=a.docentes_notificados or [],
        created_at=a.created_at,
        updated_at=a.updated_at
    )


@router.put("/{alerta_id}/estado", response_model=AlertaResponse)
async def update_estado(
    alerta_id: str,
    estado_data: AlertaEstadoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Cambiar estado de seguimiento de una alerta"""
    if not PermisoService.tiene_permiso(db, current_user, "cambiar_estado_alerta"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    a = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    a.estado_seguimiento = estado_data.estado_seguimiento
    db.commit()
    db.refresh(a)

    return AlertaResponse(
        id=str(a.id),
        estudiante_id=str(a.estudiante_id),
        materia_id=str(a.materia_id) if a.materia_id else None,
        nivel_riesgo=a.nivel_riesgo.value,
        estado_seguimiento=a.estado_seguimiento.value,
        descripcion=a.descripcion,
        periodo=a.periodo,
        promedio_anterior=float(decrypt_data(str(a.promedio_anterior))) if a.promedio_anterior else None,
        promedio_actual=float(decrypt_data(str(a.promedio_actual))) if a.promedio_actual else None,
        promedio_proyeccion=float(decrypt_data(str(a.promedio_proyeccion))) if a.promedio_proyeccion else None,
        docentes_notificados=a.docentes_notificados or [],
        created_at=a.created_at,
        updated_at=a.updated_at
    )


@router.delete("/{alerta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alerta(
    alerta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Eliminar una alerta"""
    if not PermisoService.tiene_permiso(db, current_user, "eliminar_alerta"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    a = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    db.delete(a)
    db.commit()
    return None


# Endpoints de Actividades
@router.get("/{alerta_id}/actividades", response_model=List[ActividadResponse])
async def list_actividades(
    alerta_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Listar actividades de una alerta"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_actividades"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    actividades = db.query(Actividad).filter(Actividad.alerta_id == alerta_id).order_by(Actividad.fecha_actividad.desc()).all()

    return [ActividadResponse(
        id=str(a.id),
        alerta_id=str(a.alerta_id),
        usuario_id=str(a.usuario_id),
        titulo=a.titulo,
        descripcion=a.descripcion,
        tipo=a.tipo.value,
        resultado=a.resultado,
        fecha_actividad=a.fecha_actividad,
        completada=a.completada,
        created_at=a.created_at
    ) for a in actividades]


@router.post("/{alerta_id}/actividades", response_model=ActividadResponse, status_code=status.HTTP_201_CREATED)
async def create_actividad(
    alerta_id: str,
    actividad_data: ActividadCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Crear una actividad para una alerta"""
    if not PermisoService.tiene_permiso(db, current_user, "crear_actividad"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    nueva = Actividad(
        alerta_id=alerta_id,
        usuario_id=str(current_user.id),
        titulo=actividad_data.titulo,
        descripcion=actividad_data.descripcion,
        tipo=actividad_data.tipo,
        resultado=actividad_data.resultado,
        fecha_actividad=actividad_data.fecha_actividad
    )

    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    return ActividadResponse(
        id=str(nueva.id),
        alerta_id=str(nueva.alerta_id),
        usuario_id=str(nueva.usuario_id),
        titulo=nueva.titulo,
        descripcion=nueva.descripcion,
        tipo=nueva.tipo.value,
        resultado=nueva.resultado,
        fecha_actividad=nueva.fecha_actividad,
        completada=nueva.completada,
        created_at=nueva.created_at
    )