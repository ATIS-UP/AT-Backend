"""schemas for artifact (artefacto) endpoints"""
from typing import Optional
from pydantic import BaseModel


class ArtefactoResponse(BaseModel):
    id: str
    nombre: str
    tipo: str
    url: str
    alerta_id: Optional[str] = None
    estudiante_id: Optional[str] = None
    uploaded_by: str
    created_at: Optional[str] = None


class ArtefactoListResponse(BaseModel):
    artefactos: list[ArtefactoResponse]
