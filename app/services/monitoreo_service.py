"""Service for Monitoreo Academico (#64) — queries real data from DB."""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.estudiante import Estudiante, Inscripcion, Materia, EstadoInscripcion


class MonitoreoService:
    def __init__(self, db: Session):
        self.db = db

    def materias_dificultad(self, periodo: Optional[str] = None) -> dict:
        total_estudiantes = self._count_estudiantes(periodo)
        materias = self._failed_subjects(periodo)

        total_menciones = sum(m["cantidad"] for m in materias)
        _exactas_keywords = {"algebra lineal", "calculo diferencial", "cálculo diferencial", "estadistica", "estadística"}
        exactas = sum(
            m["cantidad"] for m in materias
            if m["materia"].strip().lower() in _exactas_keywords
        )
        pct_exactas = round((exactas / total_menciones) * 100) if total_menciones else 0

        return {
            "periodo": periodo or "global",
            "total_estudiantes": total_estudiantes,
            "ingreso_familiar_promedio": self._avg_ingreso(),
            "porcentaje_ciencias_exactas": pct_exactas,
            "materias": materias,
            "total_menciones": total_menciones,
        }

    def _count_estudiantes(self, periodo: Optional[str] = None) -> int:
        q = self.db.query(Estudiante).filter(Estudiante.semestre == 1)
        if periodo:
            q = (
                q.join(Inscripcion)
                .filter(Inscripcion.periodo == periodo)
                .distinct()
            )
        return q.count()

    def _avg_ingreso(self) -> int:
        result = (
            self.db.query(func.avg(Estudiante.ingreso_familiar))
            .filter(Estudiante.ingreso_familiar.isnot(None))
            .scalar()
        )
        return int(result) if result else 0

    def _failed_subjects(self, periodo: Optional[str] = None) -> list[dict]:
        estados_fallo = {EstadoInscripcion.REPROBADO, EstadoInscripcion.CANCELADO}
        q = (
            self.db.query(Materia.nombre, func.count(Inscripcion.id).label("cantidad"))
            .join(Inscripcion, Materia.id == Inscripcion.materia_id)
            .join(Estudiante, Estudiante.id == Inscripcion.estudiante_id)
            .filter(Inscripcion.estado.in_(estados_fallo))
            .filter(Estudiante.semestre == 1)
        )
        if periodo:
            q = q.filter(Inscripcion.periodo == periodo)
        rows = q.group_by(Materia.nombre).order_by(func.count(Inscripcion.id).desc()).all()
        return [{"materia": r.nombre, "cantidad": r.cantidad} for r in rows]
