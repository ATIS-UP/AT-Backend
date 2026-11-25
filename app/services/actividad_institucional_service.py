"""Service para Actividades Institucionales"""
from datetime import UTC as tz_utc, datetime, timedelta, timezone
from typing import Optional, Tuple, List
from uuid import UUID
from sqlalchemy import case, or_
from sqlalchemy.orm import Session, joinedload

from app.models.actividad_institucional import (
    ActividadInstitucional,
    TipoActividadInstitucional,
    EstadoActividadInstitucional,
    ModalidadActividad,
)
from app.schemas.actividad_institucional import (
    ActividadInstitucionalCreate,
    ActividadInstitucionalUpdate,
    ActividadInstitucionalResponse,
)
from app.utils.security import sanitize_like_param

# Las fechas de actividades son hora de pared de Colombia (TIMESTAMP sin zona).
# Colombia es UTC-5 todo el año (sin horario de verano); se usa un desfase fijo
# porque la imagen python:slim no trae tzdata para ZoneInfo("America/Bogota").
HORA_COLOMBIA = timezone(timedelta(hours=-5), "America/Bogota")

# Una actividad cancelada o finalizada no es "próxima" aunque su fecha no haya pasado.
ESTADOS_CERRADOS = (EstadoActividadInstitucional.CANCELADA, EstadoActividadInstitucional.FINALIZADA)


def ahora_colombia() -> datetime:
    """hora actual de Colombia sin tzinfo, comparable con las columnas de fecha."""
    return datetime.now(tz_utc).astimezone(HORA_COLOMBIA).replace(tzinfo=None)


def orden_proximas_primero(ahora: datetime) -> list:
    """próximas/en curso primero (la más cercana arriba), luego pasadas (la más reciente arriba)."""
    es_proxima = (ActividadInstitucional.fecha_fin >= ahora) & ActividadInstitucional.estado.notin_(ESTADOS_CERRADOS)
    grupo = case((es_proxima, 0), else_=1)
    return [
        grupo,
        case((es_proxima, ActividadInstitucional.fecha_inicio)).asc(),
        ActividadInstitucional.fecha_inicio.desc(),
        ActividadInstitucional.created_at.desc(),
        ActividadInstitucional.id,  # desempate estable para que la paginación no repita filas
    ]


class ActividadInstitucionalService:
    def __init__(self, db: Session):
        self.db = db

    def _to_response(self, actividad: ActividadInstitucional) -> ActividadInstitucionalResponse:
        creador_nombre = actividad.creador.nombre if actividad.creador else "Desconocido"
        return ActividadInstitucionalResponse(
            id=str(actividad.id),
            tipo=actividad.tipo.value if hasattr(actividad.tipo, 'value') else str(actividad.tipo),
            fecha_inicio=actividad.fecha_inicio,
            fecha_fin=actividad.fecha_fin,
            estado=actividad.estado.value if hasattr(actividad.estado, 'value') else str(actividad.estado),
            descripcion=actividad.descripcion,
            encargado=actividad.encargado,
            observaciones=actividad.observaciones,
            anexos=actividad.anexos,
            total_anexos=len(actividad.archivos_anexos) if actividad.archivos_anexos else 0,
            creador_id=str(actividad.creador_id),
            creador_nombre=creador_nombre,
            modalidad=actividad.modalidad.value if hasattr(actividad.modalidad, 'value') else str(actividad.modalidad),
            lugar_enlace=actividad.lugar_enlace,
            created_at=actividad.created_at,
            updated_at=actividad.updated_at,
        )

    def listar(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        estado: Optional[str] = None,
        tipo: Optional[str] = None,
        buscar: Optional[str] = None,
    ) -> Tuple[List[ActividadInstitucionalResponse], int]:
        query = self.db.query(ActividadInstitucional).options(
            joinedload(ActividadInstitucional.creador),
            joinedload(ActividadInstitucional.archivos_anexos),
        )

        if estado:
            query = query.filter(ActividadInstitucional.estado == EstadoActividadInstitucional(estado))
        if tipo:
            query = query.filter(ActividadInstitucional.tipo == TipoActividadInstitucional(tipo))

        termino = buscar.strip() if buscar else ""
        if termino:
            # estas columnas no estan cifradas: se puede filtrar en SQL
            patron = f"%{sanitize_like_param(termino)}%"
            query = query.filter(or_(
                ActividadInstitucional.descripcion.ilike(patron),
                ActividadInstitucional.encargado.ilike(patron),
                ActividadInstitucional.lugar_enlace.ilike(patron),
            ))

        total = query.count()
        actividades = (
            query.order_by(*orden_proximas_primero(ahora_colombia()))
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
            .all()
        )

        return [self._to_response(a) for a in actividades], total

    def obtener(self, actividad_id: str) -> Optional[ActividadInstitucionalResponse]:
        actividad = self.db.query(ActividadInstitucional).options(
            joinedload(ActividadInstitucional.creador),
            joinedload(ActividadInstitucional.archivos_anexos),
        ).filter(
            ActividadInstitucional.id == UUID(actividad_id)
        ).first()

        if not actividad:
            return None

        return self._to_response(actividad)

    def crear(self, data: ActividadInstitucionalCreate, usuario_id: str) -> ActividadInstitucionalResponse:
        actividad = ActividadInstitucional(
            tipo=TipoActividadInstitucional(data.tipo),
            fecha_inicio=data.fecha_inicio,
            fecha_fin=data.fecha_fin,
            estado=EstadoActividadInstitucional.CREADA,
            descripcion=data.descripcion,
            encargado=data.encargado,
            observaciones=data.observaciones,
            anexos=data.anexos,
            creador_id=UUID(usuario_id),
            modalidad=ModalidadActividad(data.modalidad),
            lugar_enlace=data.lugar_enlace,
        )

        self.db.add(actividad)
        self.db.commit()
        self.db.refresh(actividad)

        return self._to_response(actividad)

    def actualizar(self, actividad_id: str, data: ActividadInstitucionalUpdate) -> Optional[ActividadInstitucionalResponse]:
        actividad = self.db.query(ActividadInstitucional).filter(
            ActividadInstitucional.id == UUID(actividad_id)
        ).first()

        if not actividad:
            return None

        if data.tipo is not None:
            actividad.tipo = TipoActividadInstitucional(data.tipo)
        if data.fecha_inicio is not None:
            actividad.fecha_inicio = data.fecha_inicio
        if data.fecha_fin is not None:
            actividad.fecha_fin = data.fecha_fin
        if data.estado is not None:
            actividad.estado = EstadoActividadInstitucional(data.estado)
        if data.descripcion is not None:
            actividad.descripcion = data.descripcion
        if data.encargado is not None:
            actividad.encargado = data.encargado
        if data.observaciones is not None:
            actividad.observaciones = data.observaciones
        if data.anexos is not None:
            actividad.anexos = data.anexos
        if data.modalidad is not None:
            actividad.modalidad = ModalidadActividad(data.modalidad)
        if data.lugar_enlace is not None:
            actividad.lugar_enlace = data.lugar_enlace

        self.db.commit()
        self.db.refresh(actividad)

        return self._to_response(actividad)

    def eliminar(self, actividad_id: str) -> bool:
        actividad = self.db.query(ActividadInstitucional).filter(
            ActividadInstitucional.id == UUID(actividad_id)
        ).first()

        if not actividad:
            return False

        self.db.delete(actividad)
        self.db.commit()

        return True
