"""Schemas de alertas y actividades"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Alertas
class AlertaBase(BaseModel):
    estudiante_id: str
    materia_id: Optional[str] = None
    nivel_riesgo: str  # ROJO, AMARILLO, VERDE
    descripcion: Optional[str] = None
    periodo: str  # 2025-1


class AlertaCreate(AlertaBase):
    promedio_anterior: Optional[float] = None
    promedio_actual: Optional[float] = None


class AlertaUpdate(BaseModel):
    nivel_riesgo: Optional[str] = None
    estado_seguimiento: Optional[str] = None
    descripcion: Optional[str] = None
    promedio_actual: Optional[float] = None
    docentes_notificados: Optional[List[str]] = None


class AlertaEstadoUpdate(BaseModel):
    estado_seguimiento: str  # PENDIENTE, EN_PROCESO, RESUELTO, DESCARTADO


class AlertaResponse(BaseModel):
    id: str
    estudiante_id: str
    materia_id: Optional[str]
    nivel_riesgo: str
    estado_seguimiento: str
    descripcion: Optional[str]
    periodo: str
    promedio_anterior: Optional[float]
    promedio_actual: Optional[float]
    promedio_proyeccion: Optional[float]
    docentes_notificados: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertaListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    alertas: List[AlertaResponse]


class AlertasStats(BaseModel):
    total: int
    critico: int
    medio: int
    bajo: int
    pendientes: int
    en_proceso: int
    resueltos: int


# Actividades
class ActividadBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    tipo: str  # LLAMADA, VISITA, REUNION, EMAIL, OTRO
    resultado: Optional[str] = None
    fecha_actividad: datetime


class ActividadCreate(ActividadBase):
    alerta_id: str


class ActividadUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    tipo: Optional[str] = None
    resultado: Optional[str] = None
    fecha_actividad: Optional[datetime] = None
    completada: Optional[bool] = None


class ActividadResponse(BaseModel):
    id: str
    alerta_id: str
    usuario_id: str
    titulo: str
    descripcion: Optional[str]
    tipo: str
    resultado: Optional[str]
    fecha_actividad: datetime
    completada: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Artefactos
class ArtefactoBase(BaseModel):
    nombre: str
    tipo: str  # DOCUMENTO, IMAGEN, PDF, OTRO
    url: str
    descripcion: Optional[str] = None


class ArtefactoCreate(ArtefactoBase):
    alerta_id: Optional[str] = None
    estudiante_id: Optional[str] = None


class ArtefactoResponse(BaseModel):
    id: str
    alerta_id: Optional[str]
    estudiante_id: Optional[str]
    nombre: str
    tipo: str
    url: str
    descripcion: Optional[str]
    uploaded_by: str
    created_at: datetime

    class Config:
        from_attributes = True