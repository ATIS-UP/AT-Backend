"""schemas for artifact (artefacto) endpoints"""
from typing import Optional
from pydantic import BaseModel
from pydantic import ConfigDict


class ArtefactoResponse(BaseModel):
    id: str
    nombre: str
    tipo: str
    url: str
    descripcion: Optional[str] = None
    alerta_id: Optional[str] = None
    estudiante_id: Optional[str] = None
    uploaded_by: str
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ArtefactoListResponse(BaseModel):
    artefactos: list[ArtefactoResponse]
