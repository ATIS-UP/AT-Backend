"""service layer for automatic alert generation based on student grades"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.alerta import Alerta, NivelRiesgo, EstadoSeguimiento
from app.models.estudiante import Inscripcion
from app.models.sistema import Parametrizacion
from app.utils.audit import AuditService
from app.exceptions import ValidationError

logger = logging.getLogger(__name__)


class AlertaAutomaticaService:
    """evaluates student grades against thresholds and generates alerts automatically"""

    def __init__(self, db: Session):
        self.db = db

    def evaluar_notas_periodo(self, periodo: str) -> list[dict]:
        """evaluate all student grades for a period against configured thresholds.

        1. reads thresholds from parametrizacion
        2. queries all inscripciones for the given periodo
        3. calculates average per student
        4. classifies risk level
        5. creates or updates alerts
        6. returns list of created/updated alert summaries
        """
        umbrales = self._obtener_umbrales()

        # get all inscripciones for the period that have at least one grade
        inscripciones = (
            self.db.query(Inscripcion)
            .filter(Inscripcion.periodo == periodo)
            .all()
        )

        # group inscripciones by student
        estudiantes_notas: dict[str, list[float]] = {}
        estudiantes_materias: dict[str, list[str]] = {}
        for insc in inscripciones:
            est_id = str(insc.estudiante_id)
            # collect available grades
            notas = []
            for nota_field in (insc.nota1, insc.nota2, insc.nota3, insc.nota_final):
                if nota_field is not None:
                    try:
                        notas.append(float(nota_field))
                    except (ValueError, TypeError):
                        continue

            if notas:
                if est_id not in estudiantes_notas:
                    estudiantes_notas[est_id] = []
                    estudiantes_materias[est_id] = []
                estudiantes_notas[est_id].extend(notas)
                estudiantes_materias[est_id].append(str(insc.materia_id))

        # evaluate each student
        resultados = []
        for estudiante_id, notas in estudiantes_notas.items():
            promedio = sum(notas) / len(notas)
            nivel = self._clasificar_riesgo(promedio, umbrales)

            if nivel is None:
                # no alert needed, student is above thresholds
                continue

            alerta = self._crear_o_actualizar_alerta(
                estudiante_id=estudiante_id,
                materia_id=estudiantes_materias[estudiante_id][0] if estudiantes_materias[estudiante_id] else None,
                nivel=nivel,
                periodo=periodo,
                promedio=promedio,
            )

            resultados.append({
                "alerta_id": str(alerta.id),
                "estudiante_id": estudiante_id,
                "nivel_riesgo": nivel,
                "promedio": round(promedio, 2),
                "periodo": periodo,
                "accion": "actualizada" if alerta.updated_at != alerta.created_at else "creada",
            })

        return resultados

    def _obtener_umbrales(self) -> dict:
        """read threshold values from parametrizacion table.

        returns dict with keys 'rojo' and 'amarillo' as floats.
        raises ValidationError if thresholds are not configured or invalid.
        """
        rojo_param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.clave == "UMBRAL_ROJO")
            .first()
        )
        amarillo_param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.clave == "UMBRAL_AMARILLO")
            .first()
        )

        if not rojo_param:
            raise ValidationError(
                "Umbral rojo no configurado en parametrización",
                fields={"UMBRAL_ROJO": "no encontrado"},
            )
        if not amarillo_param:
            raise ValidationError(
                "Umbral amarillo no configurado en parametrización",
                fields={"UMBRAL_AMARILLO": "no encontrado"},
            )

        try:
            rojo = float(rojo_param.valor)
        except (ValueError, TypeError):
            raise ValidationError(
                "UMBRAL_ROJO no contiene un valor numérico válido",
                fields={"UMBRAL_ROJO": rojo_param.valor},
            )

        try:
            amarillo = float(amarillo_param.valor)
        except (ValueError, TypeError):
            raise ValidationError(
                "UMBRAL_AMARILLO no contiene un valor numérico válido",
                fields={"UMBRAL_AMARILLO": amarillo_param.valor},
            )

        return {"rojo": rojo, "amarillo": amarillo}

    def _clasificar_riesgo(self, promedio: float, umbrales: dict) -> Optional[str]:
        """classify risk level based on average and thresholds.

        returns NivelRiesgo value string or None if no alert needed.
        - promedio < umbral_rojo -> ROJO
        - umbral_rojo <= promedio < umbral_amarillo -> AMARILLO
        - promedio >= umbral_amarillo -> None (no alert)
        """
        if promedio < umbrales["rojo"]:
            return NivelRiesgo.ROJO.value
        elif promedio < umbrales["amarillo"]:
            return NivelRiesgo.AMARILLO.value
        return None

    def _crear_o_actualizar_alerta(
        self,
        estudiante_id: str,
        materia_id: Optional[str],
        nivel: str,
        periodo: str,
        promedio: float,
    ) -> Alerta:
        """create a new alert or update an existing active one for the same student/period.

        deduplication: checks for an active alert (PENDIENTE or EN_PROCESO)
        for the same estudiante_id + periodo. if found, updates nivel_riesgo.
        if not, creates a new alert.

        logs to audit with origen="SISTEMA".
        """
        # check for existing active alert for this student and period
        existing = (
            self.db.query(Alerta)
            .filter(
                and_(
                    Alerta.estudiante_id == estudiante_id,
                    Alerta.periodo == periodo,
                    Alerta.estado_seguimiento.in_([
                        EstadoSeguimiento.PENDIENTE,
                        EstadoSeguimiento.EN_PROCESO,
                    ]),
                )
            )
            .first()
        )

        if existing:
            # update existing alert
            existing.nivel_riesgo = nivel
            existing.promedio_actual = promedio
            self.db.commit()
            self.db.refresh(existing)

            AuditService.log(
                db=self.db,
                usuario_id=None,
                accion="UPDATE",
                entidad="Alerta",
                entidad_id=str(existing.id),
                detalles={
                    "origen": "SISTEMA",
                    "nivel_riesgo": nivel,
                    "promedio": round(promedio, 2),
                    "periodo": periodo,
                },
                estado="EXITOSO",
                mensaje="Alerta actualizada automáticamente por evaluación de notas",
            )

            return existing

        # create new alert
        nueva = Alerta(
            estudiante_id=estudiante_id,
            materia_id=materia_id,
            nivel_riesgo=nivel,
            estado_seguimiento=EstadoSeguimiento.PENDIENTE,
            descripcion=f"Alerta generada automáticamente. Promedio: {round(promedio, 2)}",
            periodo=periodo,
            promedio_actual=promedio,
        )

        self.db.add(nueva)
        self.db.commit()
        self.db.refresh(nueva)

        AuditService.log(
            db=self.db,
            usuario_id=None,
            accion="CREATE",
            entidad="Alerta",
            entidad_id=str(nueva.id),
            detalles={
                "origen": "SISTEMA",
                "nivel_riesgo": nivel,
                "promedio": round(promedio, 2),
                "periodo": periodo,
                "estudiante_id": estudiante_id,
            },
            estado="EXITOSO",
            mensaje="Alerta creada automáticamente por evaluación de notas",
        )

        return nueva
