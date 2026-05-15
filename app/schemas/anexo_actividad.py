"""Schemas para Anexos de Actividades Institucionales"""
from typing import Optional, List
from pydantic import BaseModel


class AnexoActividadResponse(BaseModel):
    id: str
    actividad_id: str
    nombre: str
    tipo: str
    url: str
    uploaded_by: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class AnexoActividadListResponse(BaseModel):
    anexos: List[AnexoActividadResponse]
    total: int
