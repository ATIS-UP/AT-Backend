"""schemas for survey (encuesta) endpoints"""
from typing import Optional
from pydantic import BaseModel


class PreguntaEncuesta(BaseModel):
    id: int
    texto: str
    tipo: str  # opcion_multiple, texto_libre, escala_likert
    opciones: Optional[list[str]] = None
    requerida: bool = True


class EncuestaCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    preguntas: list[PreguntaEncuesta]
    periodo: Optional[str] = None


class EncuestaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    preguntas: Optional[list[PreguntaEncuesta]] = None
    periodo: Optional[str] = None


class EncuestaResponse(BaseModel):
    id: str
    titulo: str
    descripcion: Optional[str] = None
    preguntas: list[dict] = []
    estado: str
    periodo: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    es_publica: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EncuestaListResponse(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    encuestas: list[EncuestaResponse]


class RespuestaCreate(BaseModel):
    respuestas: list[dict]


class ResultadoPregunta(BaseModel):
    pregunta_id: int
    texto: str
    tipo: str
    total_respuestas: int
    distribucion: Optional[dict] = None
    promedio: Optional[float] = None
    respuestas_texto: Optional[list[str]] = None


class EncuestaResultados(BaseModel):
    encuesta_id: str
    titulo: str
    total_respuestas: int
    resultados_por_pregunta: list[ResultadoPregunta]
