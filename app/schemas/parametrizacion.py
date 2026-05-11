"""schemas for system parametrization endpoints"""
from typing import Optional
from pydantic import BaseModel


class ParametrizacionResponse(BaseModel):
    id: str
    clave: str
    valor: str
    descripcion: Optional[str] = None
    tipo: str
    updated_at: Optional[str] = None
    created_at: Optional[str] = None


class ParametrizacionUpdate(BaseModel):
    valor: str


class ParametrizacionGroupResponse(BaseModel):
    grupo: str
    parametros: list[ParametrizacionResponse]
