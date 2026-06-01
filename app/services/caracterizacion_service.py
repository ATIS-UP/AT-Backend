"""Service for socioeconomic characterization aggregations."""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.estudiante import Estudiante, EstadoEstudiante


class CaracterizacionService:
    def __init__(self, db: Session):
        self.db = db

    def _activos(self):
        return (
            self.db.query(Estudiante)
            .filter(Estudiante.estado == EstadoEstudiante.ACTIVO)
            .all()
        )

    def socioeconomica(self, periodo: Optional[str] = None) -> dict:
        estudiantes = self._activos()
        total = len(estudiantes)

        por_estrato: dict[int, int] = {}
        for e in estudiantes:
            if e.estrato is not None:
                por_estrato[e.estrato] = por_estrato.get(e.estrato, 0) + 1

        bajo = sum(por_estrato.get(i, 0) for i in [1, 2])
        medio = sum(por_estrato.get(i, 0) for i in [3, 4])
        alto = sum(por_estrato.get(i, 0) for i in [5, 6])

        return {
            "periodo": periodo,
            "total_estudiantes": total,
            "por_estrato": [
                {"estrato": k, "label": f"Estrato {k}", "cantidad": v}
                for k, v in sorted(por_estrato.items())
            ],
            "agrupado": [
                {"grupo": "Bajo (1-2)", "cantidad": bajo},
                {"grupo": "Medio (3-4)", "cantidad": medio},
                {"grupo": "Alto (5-6)", "cantidad": alto},
            ],
        }

    def procedencia(self, periodo: Optional[str] = None) -> dict:
        estudiantes = self._activos()
        total = len(estudiantes)

        locales = sum(1 for e in estudiantes if e.procedencia == "LOCAL")
        foraneos = sum(1 for e in estudiantes if e.procedencia == "FORANEO")

        return {
            "periodo": periodo,
            "total_estudiantes": total,
            "datos": [
                {"procedencia": "Locales", "codigo": "LOCAL", "cantidad": locales},
                {"procedencia": "Foráneos", "codigo": "FORANEO", "cantidad": foraneos},
            ],
        }

    def genero(self, periodo: Optional[str] = None) -> dict:
        estudiantes = self._activos()
        total = len(estudiantes)

        h = sum(1 for e in estudiantes if e.genero == "H")
        m = sum(1 for e in estudiantes if e.genero == "M")
        otro = sum(1 for e in estudiantes if e.genero == "OTRO")

        return {
            "periodo": periodo,
            "total_estudiantes": total,
            "datos": [
                {"genero": "Hombre", "codigo": "H", "cantidad": h},
                {"genero": "Mujer", "codigo": "M", "cantidad": m},
                {"genero": "Otro", "codigo": "OTRO", "cantidad": otro},
            ],
        }
