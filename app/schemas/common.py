"""common shared schemas used across multiple endpoints"""
from typing import Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    message: str
    error_code: str
    status_code: int
    details: Optional[dict] = None
    timestamp: str


class CargaMasivaResumen(BaseModel):
    total_filas: int
    insertadas: int
    actualizadas: int
    errores: int
    detalle_errores: list[dict]
