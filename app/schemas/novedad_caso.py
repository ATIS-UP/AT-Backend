"""Schemas para Novedades de Casos Especiales"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class NovedadCasoCreate(BaseModel):
    tipo_caso: str
    nombre: str
    orden: int = 0


class NovedadCasoUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None
    orden: Optional[int] = None


class NovedadCasoResponse(BaseModel):
    id: str
    tipo_caso: str
    nombre: str
    activo: bool
    orden: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
