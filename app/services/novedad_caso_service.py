"""Service para Novedades de Casos Especiales"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.novedad_caso import NovedadCaso
from app.schemas.novedad_caso import NovedadCasoCreate, NovedadCasoUpdate, NovedadCasoResponse


class NovedadCasoService:
    def __init__(self, db: Session):
        self.db = db

    def _to_response(self, n: NovedadCaso) -> NovedadCasoResponse:
        return NovedadCasoResponse(
            id=str(n.id),
            tipo_caso=n.tipo_caso,
            nombre=n.nombre,
            activo=n.activo,
            orden=n.orden,
            created_at=n.created_at,
        )

    def listar(self, tipo_caso: Optional[str] = None, solo_activos: bool = False) -> List[NovedadCasoResponse]:
        query = self.db.query(NovedadCaso).order_by(NovedadCaso.tipo_caso, NovedadCaso.orden)
        if tipo_caso:
            query = query.filter(NovedadCaso.tipo_caso == tipo_caso)
        if solo_activos:
            query = query.filter(NovedadCaso.activo == True)
        return [self._to_response(n) for n in query.all()]

    def crear(self, data: NovedadCasoCreate) -> NovedadCasoResponse:
        novedad = NovedadCaso(
            tipo_caso=data.tipo_caso,
            nombre=data.nombre,
            orden=data.orden,
        )
        self.db.add(novedad)
        self.db.commit()
        self.db.refresh(novedad)
        return self._to_response(novedad)

    def actualizar(self, novedad_id: str, data: NovedadCasoUpdate) -> Optional[NovedadCasoResponse]:
        novedad = self.db.query(NovedadCaso).filter(NovedadCaso.id == UUID(novedad_id)).first()
        if not novedad:
            return None
        if data.nombre is not None:
            novedad.nombre = data.nombre
        if data.activo is not None:
            novedad.activo = data.activo
        if data.orden is not None:
            novedad.orden = data.orden
        self.db.commit()
        self.db.refresh(novedad)
        return self._to_response(novedad)

    def eliminar(self, novedad_id: str) -> bool:
        novedad = self.db.query(NovedadCaso).filter(NovedadCaso.id == UUID(novedad_id)).first()
        if not novedad:
            return False
        self.db.delete(novedad)
        self.db.commit()
        return True
