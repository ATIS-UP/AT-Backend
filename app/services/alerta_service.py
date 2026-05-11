"""service layer for alert operations"""
from typing import Optional
from sqlalchemy.orm import Session

from app.exceptions import EntityNotFoundError
from app.models.alerta import Alerta, Actividad, NivelRiesgo, EstadoSeguimiento
from app.models.estudiante import Estudiante
from app.schemas.alerta import (
    AlertaCreate,
    AlertaUpdate,
    AlertaResponse,
    AlertaEstadoUpdate,
    AlertasStats,
    ActividadCreate,
    ActividadResponse,
)
from app.utils.security import encrypt_data, decrypt_data
from app.utils.audit import AuditService


class AlertaService:
    """encapsulates business logic for alerts and activities"""

    def __init__(self, db: Session):
        self.db = db

    # -- helpers --

    def _to_response(self, alerta: Alerta) -> AlertaResponse:
        """convert an alerta orm instance to response schema"""
        return AlertaResponse(
            id=str(alerta.id),
            estudiante_id=str(alerta.estudiante_id),
            materia_id=str(alerta.materia_id) if alerta.materia_id else None,
            nivel_riesgo=alerta.nivel_riesgo.value,
            estado_seguimiento=alerta.estado_seguimiento.value,
            descripcion=alerta.descripcion,
            periodo=alerta.periodo,
            promedio_anterior=self._decrypt_promedio(alerta.promedio_anterior),
            promedio_actual=self._decrypt_promedio(alerta.promedio_actual),
            promedio_proyeccion=self._decrypt_promedio(alerta.promedio_proyeccion),
            docentes_notificados=alerta.docentes_notificados or [],
            created_at=alerta.created_at,
            updated_at=alerta.updated_at,
        )

    def _decrypt_promedio(self, value) -> Optional[float]:
        """decrypt a promedio field, return none if empty"""
        if not value:
            return None
        decrypted = decrypt_data(str(value))
        if decrypted == "[DATO_CORRUPTO]":
            return None
        try:
            return float(decrypted)
        except (ValueError, TypeError):
            return None

    def _actividad_to_response(self, actividad: Actividad) -> ActividadResponse:
        """convert an actividad orm instance to response schema"""
        return ActividadResponse(
            id=str(actividad.id),
            alerta_id=str(actividad.alerta_id),
            usuario_id=str(actividad.usuario_id),
            titulo=actividad.titulo,
            descripcion=actividad.descripcion,
            tipo=actividad.tipo.value,
            resultado=actividad.resultado,
            fecha_actividad=actividad.fecha_actividad,
            completada=actividad.completada,
            created_at=actividad.created_at,
        )

    # -- crud operations --

    def listar(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        nivel_riesgo: Optional[str] = None,
        estado_seguimiento: Optional[str] = None,
        periodo: Optional[str] = None,
    ) -> tuple[list[AlertaResponse], int]:
        """query alerts with filters, decrypt promedios, paginate"""
        query = self.db.query(Alerta)

        if nivel_riesgo:
            query = query.filter(Alerta.nivel_riesgo == nivel_riesgo)
        if estado_seguimiento:
            query = query.filter(Alerta.estado_seguimiento == estado_seguimiento)
        if periodo:
            query = query.filter(Alerta.periodo == periodo)

        total = query.count()
        alertas = (
            query.order_by(Alerta.created_at.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
            .all()
        )

        resultados = [self._to_response(a) for a in alertas]
        return resultados, total

    def obtener(self, alerta_id: str) -> AlertaResponse:
        """get a single alert by id, raises EntityNotFoundError if missing"""
        alerta = self.db.query(Alerta).filter(Alerta.id == alerta_id).first()
        if not alerta:
            raise EntityNotFoundError("Alerta", alerta_id)
        return self._to_response(alerta)

    def crear(
        self, data: AlertaCreate, usuario_id: str, ip: str
    ) -> AlertaResponse:
        """create a new alert, validate estudiante exists, encrypt promedios"""
        estudiante = (
            self.db.query(Estudiante)
            .filter(Estudiante.id == data.estudiante_id)
            .first()
        )
        if not estudiante:
            raise EntityNotFoundError("Estudiante", data.estudiante_id)

        nueva = Alerta(
            estudiante_id=data.estudiante_id,
            materia_id=data.materia_id,
            nivel_riesgo=data.nivel_riesgo,
            descripcion=data.descripcion,
            periodo=data.periodo,
            promedio_anterior=(
                encrypt_data(str(data.promedio_anterior))
                if data.promedio_anterior is not None
                else None
            ),
            promedio_actual=(
                encrypt_data(str(data.promedio_actual))
                if data.promedio_actual is not None
                else None
            ),
        )

        self.db.add(nueva)
        self.db.commit()
        self.db.refresh(nueva)

        AuditService.log_crear(
            self.db,
            usuario_id,
            "Alerta",
            str(nueva.id),
            {
                "estudiante_id": str(nueva.estudiante_id),
                "nivel_riesgo": nueva.nivel_riesgo.value,
                "periodo": nueva.periodo,
            },
            ip,
        )

        return self._to_response(nueva)

    def actualizar(
        self, alerta_id: str, data: AlertaUpdate, usuario_id: str, ip: str
    ) -> AlertaResponse:
        """update an alert, encrypt promedios if updated"""
        alerta = self.db.query(Alerta).filter(Alerta.id == alerta_id).first()
        if not alerta:
            raise EntityNotFoundError("Alerta", alerta_id)

        update_fields = data.model_dump(exclude_unset=True)
        encrypted_fields = {"promedio_actual", "promedio_proyeccion"}

        for key, value in update_fields.items():
            if key in encrypted_fields:
                setattr(
                    alerta,
                    key,
                    encrypt_data(str(value)) if value is not None else None,
                )
            else:
                setattr(alerta, key, value)

        self.db.commit()
        self.db.refresh(alerta)

        AuditService.log_actualizar(
            self.db,
            usuario_id,
            "Alerta",
            str(alerta.id),
            {},
            update_fields,
            ip,
        )

        return self._to_response(alerta)

    def cambiar_estado(
        self, alerta_id: str, nuevo_estado: str, usuario_id: str, ip: str
    ) -> AlertaResponse:
        """update the follow-up state of an alert"""
        alerta = self.db.query(Alerta).filter(Alerta.id == alerta_id).first()
        if not alerta:
            raise EntityNotFoundError("Alerta", alerta_id)

        estado_anterior = alerta.estado_seguimiento.value
        alerta.estado_seguimiento = nuevo_estado
        self.db.commit()
        self.db.refresh(alerta)

        AuditService.log_actualizar(
            self.db,
            usuario_id,
            "Alerta",
            str(alerta.id),
            {"estado_seguimiento": estado_anterior},
            {"estado_seguimiento": nuevo_estado},
            ip,
        )

        return self._to_response(alerta)

    def eliminar(self, alerta_id: str, usuario_id: str, ip: str) -> None:
        """delete an alert, raises EntityNotFoundError if missing"""
        alerta = self.db.query(Alerta).filter(Alerta.id == alerta_id).first()
        if not alerta:
            raise EntityNotFoundError("Alerta", alerta_id)

        AuditService.log_eliminar(
            self.db,
            usuario_id,
            "Alerta",
            str(alerta.id),
            {
                "estudiante_id": str(alerta.estudiante_id),
                "nivel_riesgo": alerta.nivel_riesgo.value,
                "periodo": alerta.periodo,
            },
            ip,
        )

        self.db.delete(alerta)
        self.db.commit()

    def get_stats(self) -> AlertasStats:
        """count alerts by risk level and follow-up state"""
        total = self.db.query(Alerta).count()
        critico = (
            self.db.query(Alerta)
            .filter(Alerta.nivel_riesgo == NivelRiesgo.ROJO)
            .count()
        )
        medio = (
            self.db.query(Alerta)
            .filter(Alerta.nivel_riesgo == NivelRiesgo.AMARILLO)
            .count()
        )
        bajo = (
            self.db.query(Alerta)
            .filter(Alerta.nivel_riesgo == NivelRiesgo.VERDE)
            .count()
        )
        pendientes = (
            self.db.query(Alerta)
            .filter(Alerta.estado_seguimiento == EstadoSeguimiento.PENDIENTE)
            .count()
        )
        en_proceso = (
            self.db.query(Alerta)
            .filter(Alerta.estado_seguimiento == EstadoSeguimiento.EN_PROCESO)
            .count()
        )
        resueltos = (
            self.db.query(Alerta)
            .filter(Alerta.estado_seguimiento == EstadoSeguimiento.RESUELTO)
            .count()
        )

        return AlertasStats(
            total=total,
            critico=critico,
            medio=medio,
            bajo=bajo,
            pendientes=pendientes,
            en_proceso=en_proceso,
            resueltos=resueltos,
        )

    # -- activity operations --

    def registrar_actividad(
        self, alerta_id: str, data: ActividadCreate, usuario_id: str
    ) -> ActividadResponse:
        """create an activity record for an alert"""
        alerta = self.db.query(Alerta).filter(Alerta.id == alerta_id).first()
        if not alerta:
            raise EntityNotFoundError("Alerta", alerta_id)

        nueva = Actividad(
            alerta_id=alerta_id,
            usuario_id=usuario_id,
            titulo=data.titulo,
            descripcion=data.descripcion,
            tipo=data.tipo,
            resultado=data.resultado,
            fecha_actividad=data.fecha_actividad,
        )

        self.db.add(nueva)
        self.db.commit()
        self.db.refresh(nueva)

        return self._actividad_to_response(nueva)

    def listar_actividades(self, alerta_id: str) -> list[ActividadResponse]:
        """list all activities for an alert ordered by date descending"""
        actividades = (
            self.db.query(Actividad)
            .filter(Actividad.alerta_id == alerta_id)
            .order_by(Actividad.fecha_actividad.desc())
            .all()
        )

        return [self._actividad_to_response(a) for a in actividades]
