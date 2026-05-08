"""Utilidades de auditoría"""
import json
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.models.sistema import Auditoria


class AuditService:
    """Servicio de auditoría para registrar acciones"""

    @staticmethod
    def log(
        db: Session,
        usuario_id: Optional[str],
        accion: str,
        entidad: str,
        entidad_id: Optional[str] = None,
        detalles: Optional[dict] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        estado: str = "EXITOSO",
        mensaje: Optional[str] = None
    ) -> Auditoria:
        """Registra una acción en la tabla de auditoría"""
        auditoria = Auditoria(
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalles=detalles,
            ip=ip,
            user_agent=user_agent,
            estado=estado,
            mensaje=mensaje
        )
        db.add(auditoria)
        db.commit()
        db.refresh(auditoria)
        return auditoria

    @staticmethod
    def log_login(db: Session, usuario_id: str, email: str, exitosa: bool, ip: Optional[str] = None):
        """Registra un intento de login"""
        return AuditService.log(
            db=db,
            usuario_id=usuario_id if exitosa else None,
            accion="LOGIN",
            entidad="Auth",
            detalles={"email": email},
            ip=ip,
            estado="EXITOSO" if exitosa else "FALLIDO",
            mensaje="Login exitoso" if exitosa else "Credenciales incorrectas"
        )

    @staticmethod
    def log_logout(db: Session, usuario_id: str, ip: Optional[str] = None):
        """Registra un logout"""
        return AuditService.log(
            db=db,
            usuario_id=usuario_id,
            accion="LOGOUT",
            entidad="Auth",
            ip=ip,
            estado="EXITOSO",
            mensaje="Logout exitoso"
        )

    @staticmethod
    def log_crear(db: Session, usuario_id: str, entidad: str, entidad_id: str, datos: dict, ip: Optional[str] = None):
        """Registra creación de entidad"""
        return AuditService.log(
            db=db,
            usuario_id=usuario_id,
            accion="CREATE",
            entidad=entidad,
            entidad_id=entidad_id,
            detalles={"datos_nuevos": datos},
            ip=ip,
            estado="EXITOSO",
            mensaje=f"Creó {entidad}"
        )

    @staticmethod
    def log_actualizar(db: Session, usuario_id: str, entidad: str, entidad_id: str, datos_anteriores: dict, datos_nuevos: dict, ip: Optional[str] = None):
        """Registra actualización de entidad"""
        return AuditService.log(
            db=db,
            usuario_id=usuario_id,
            accion="UPDATE",
            entidad=entidad,
            entidad_id=entidad_id,
            detalles={"datos_anteriores": datos_anteriores, "datos_nuevos": datos_nuevos},
            ip=ip,
            estado="EXITOSO",
            mensaje=f"Actualizó {entidad}"
        )

    @staticmethod
    def log_eliminar(db: Session, usuario_id: str, entidad: str, entidad_id: str, datos_eliminados: dict, ip: Optional[str] = None):
        """Registra eliminación de entidad"""
        return AuditService.log(
            db=db,
            usuario_id=usuario_id,
            accion="DELETE",
            entidad=entidad,
            entidad_id=entidad_id,
            detalles={"datos_eliminados": datos_eliminados},
            ip=ip,
            estado="EXITOSO",
            mensaje=f"Eliminó {entidad}"
        )

    @staticmethod
    def log_error(db: Session, usuario_id: Optional[str], accion: str, entidad: str, error: str, ip: Optional[str] = None):
        """Registra un error"""
        return AuditService.log(
            db=db,
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            detalles={"error": error},
            ip=ip,
            estado="FALLIDO",
            mensaje=error
        )