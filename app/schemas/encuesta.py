"""schemas for survey (encuesta) endpoints"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PreguntaEncuesta(BaseModel):
    id: Optional[int] = None
    texto: str
    tipo: str  # opcion_multiple, texto_libre, escala_likert, ABIERTA
    opciones: Optional[list[str]] = None
    requerida: bool = True


class EncuestaCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    preguntas: list[PreguntaEncuesta]
    periodo: Optional[str] = None
    fecha_fin: Optional[datetime] = None


class EncuestaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    preguntas: Optional[list[PreguntaEncuesta]] = None
    periodo: Optional[str] = None
    fecha_fin: Optional[datetime] = None


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


class InfoPublicaResponse(BaseModel):
    id: str
    titulo: str
    descripcion: Optional[str] = None
    preguntas: list[dict] = []


class VerificarEstudianteRequest(BaseModel):
    documento: str = Field(..., min_length=1, max_length=50)


class VerificarEstudianteResponse(BaseModel):
    existe: bool
    ya_respondio: bool = False
    puede_responder: bool = False
    estudiante_nombre: Optional[str] = None
    estudiante_id: Optional[str] = None


class ResponderEncuestaPublica(BaseModel):
    documento: str = Field(..., min_length=1, max_length=50)
    respuestas: list[dict]


class ProcesarVencimientosResponse(BaseModel):
    cerradas: int
    procesadas: int
    fecha_referencia: str
