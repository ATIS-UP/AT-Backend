"""Schemas para Registros de Casos Especiales"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class EstudianteInfo(BaseModel):
    id: str
    codigo: str
    documento: Optional[str] = None
    nombres: str
    apellidos: str
    programa: str
    semestre: int
    estado: str

    class Config:
        from_attributes = True


class RegistroCasoCreate(BaseModel):
    estudiante_id: str
    tipo: str
    observaciones: Optional[str] = None


class RegistroCasoUpdate(BaseModel):
    tipo: Optional[str] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None


class RegistroCasoResponse(BaseModel):
    id: str
    estudiante_id: str
    estudiante: EstudianteInfo
    tipo: str
    estado: str
    observaciones: Optional[str] = None
    responsable_id: str
    responsable_nombre: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RegistroCasoListResponse(BaseModel):
    registros: List[RegistroCasoResponse]
    total: int
    pagina: int
    por_pagina: int


class BusquedaEstudianteResponse(BaseModel):
    estudiante: EstudianteInfo
    registros: List[RegistroCasoResponse]
    total_registros: int


class HistorialCreate(BaseModel):
    accion: str
    observaciones: Optional[str] = None


class HistorialResponse(BaseModel):
    id: str
    registro_id: str
    accion: str
    observaciones: Optional[str] = None
    responsable_id: str
    responsable_nombre: str
    created_at: datetime

    class Config:
        from_attributes = True


class HistorialListResponse(BaseModel):
    historiales: List[HistorialResponse]
    total: int