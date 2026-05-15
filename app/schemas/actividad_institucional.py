"""Schemas para Actividades Institucionales"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class ActividadInstitucionalCreate(BaseModel):
    tipo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    descripcion: str
    encargado: str
    observaciones: Optional[str] = None
    anexos: Optional[str] = None
    modalidad: str
    lugar_enlace: str


class ActividadInstitucionalUpdate(BaseModel):
    tipo: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    estado: Optional[str] = None
    descripcion: Optional[str] = None
    encargado: Optional[str] = None
    observaciones: Optional[str] = None
    anexos: Optional[str] = None
    modalidad: Optional[str] = None
    lugar_enlace: Optional[str] = None


class ActividadInstitucionalResponse(BaseModel):
    id: str
    tipo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str
    descripcion: str
    encargado: str
    observaciones: Optional[str] = None
    anexos: Optional[str] = None
    total_anexos: int = 0
    creador_id: str
    creador_nombre: str
    modalidad: str
    lugar_enlace: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActividadInstitucionalListResponse(BaseModel):
    actividades: List[ActividadInstitucionalResponse]
    total: int
    pagina: int
    por_pagina: int
