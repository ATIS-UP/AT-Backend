"""Schemas para Novedades de Casos Especiales"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NovedadCasoCreate(BaseModel):
    tipo_caso: str
    nombre: str
    descripcion: Optional[str] = None
    orden: int = 0


class NovedadCasoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None
    orden: Optional[int] = None


class NovedadCasoResponse(BaseModel):
    id: str
    tipo_caso: str
    nombre: str
    descripcion: Optional[str] = None
    activo: bool
    orden: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
