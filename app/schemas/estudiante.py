"""Schemas de estudiantes"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class EstudianteBase(BaseModel):
    codigo: str
    nombres: str
    apellidos: str
    email: Optional[str] = None
    documento: Optional[str] = None
    telefono: Optional[str] = None
    programa: str
    semestre: int = 1
    promedio_general: Optional[float] = None
    promedio_acumulado: Optional[float] = None
    estado: str = "ACTIVO"


class EstudianteCreate(EstudianteBase):
    pass


class EstudianteUpdate(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    documento: Optional[str] = None
    telefono: Optional[str] = None
    programa: Optional[str] = None
    semestre: Optional[int] = None
    promedio_general: Optional[float] = None
    promedio_acumulado: Optional[float] = None
    estado: Optional[str] = None


class EstudianteResponse(BaseModel):
    id: str
    codigo: str
    nombres: str
    apellidos: str
    email: Optional[str]
    documento: Optional[str]
    telefono: Optional[str]
    programa: str
    semestre: int
    promedio_general: Optional[float]
    promedio_acumulado: Optional[float]
    estado: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EstudianteListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    estudiantes: List[EstudianteResponse]


# Materia
class MateriaBase(BaseModel):
    codigo: str
    nombre: str
    programa: Optional[str] = None
    creditos: int = 0


class MateriaResponse(BaseModel):
    id: str
    codigo: str
    nombre: str
    programa: Optional[str]
    creditos: int

    class Config:
        from_attributes = True


# Inscripción
class InscripcionBase(BaseModel):
    estudiante_id: str
    materia_id: str
    periodo: str
    nota_final: Optional[float] = None
    estado: str = "EN_CURSO"


class InscripcionResponse(BaseModel):
    id: str
    estudiante_id: str
    materia_id: str
    materia: Optional[MateriaResponse] = None
    periodo: str
    nota_final: Optional[float]
    estado: str

    class Config:
        from_attributes = True


class HistorialAcademico(BaseModel):
    estudiante: EstudianteResponse
    inscripciones: List[InscripcionResponse]
    promedio_general: Optional[float]