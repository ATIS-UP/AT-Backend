"""Service para Registros de Casos Especiales"""
from typing import Optional, Tuple, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.caso_especial import (
    RegistroCasoEspecial, HistorialRegistro,
    TipoRegistroCaso, EstadoRegistroCaso, AccionHistorial
)
from app.models.estudiante import Estudiante
from app.schemas.caso_especial import (
    RegistroCasoCreate, RegistroCasoUpdate,
    RegistroCasoResponse, EstudianteInfo
)
from app.utils.security import decrypt_data


class CasoEspecialService:
    def __init__(self, db: Session):
        self.db = db

    def _estudiante_to_info(self, estudiante: Estudiante) -> EstudianteInfo:
        return EstudianteInfo(
            id=str(estudiante.id),
            codigo=estudiante.codigo,
            documento=decrypt_data(estudiante.documento) if estudiante.documento else None,
            nombres=decrypt_data(estudiante.nombres),
            apellidos=decrypt_data(estudiante.apellidos),
            programa=estudiante.programa,
            semestre=estudiante.semestre,
            estado=estudiante.estado.value if hasattr(estudiante.estado, 'value') else str(estudiante.estado)
        )

    def _registro_to_response(self, registro: RegistroCasoEspecial) -> RegistroCasoResponse:
        return RegistroCasoResponse(
            id=str(registro.id),
            estudiante_id=str(registro.estudiante_id),
            estudiante=self._estudiante_to_info(registro.estudiante) if registro.estudiante else None,
            tipo=registro.tipo.value if hasattr(registro.tipo, 'value') else str(registro.tipo),
            estado=registro.estado.value if hasattr(registro.estado, 'value') else str(registro.estado),
            observaciones=registro.observaciones,
            responsable_id=str(registro.responsable_id),
            responsable_nombre=registro.responsable_nombre,
            created_at=registro.created_at,
            updated_at=registro.updated_at
        )

    def buscar_estudiantes(self, q: str, pagina: int = 1, por_pagina: int = 20) -> Tuple[List, int]:
        if not q:
            return [], 0
        
        q_lower = q.lower().strip()
        
        # Obtener todos los estudiantes y filtrar en Python después de desencriptar
        estudiantes = self.db.query(Estudiante).all()
        
        estudiantes = [
            est for est in estudiantes
            if self._matches_search(self._estudiante_to_info(est), q_lower)
        ]
        
        estudiante_ids = [est.id for est in estudiantes]
        registros_dict = {}
        if estudiante_ids:
            registros = self.db.query(RegistroCasoEspecial).filter(
                RegistroCasoEspecial.estudiante_id.in_(estudiante_ids)
            ).order_by(RegistroCasoEspecial.created_at.desc()).all()
            for reg in registros:
                eid = str(reg.estudiante_id)
                if eid not in registros_dict:
                    registros_dict[eid] = []
                registros_dict[eid].append(reg)
        
        resultados = []
        for est in estudiantes:
            est_info = self._estudiante_to_info(est)
            est_id_str = str(est.id)
            regs = registros_dict.get(est_id_str, [])
            
            resultados.append({
                "estudiante": est_info,
                "registros": [self._registro_to_response(r) for r in regs],
                "total_registros": len(regs)
            })
        
        total = len(resultados)
        start = (pagina - 1) * por_pagina
        end = start + por_pagina
        resultados_pagina = resultados[start:end]
        
        return resultados_pagina, total
    
    def _matches_search(self, est_info: EstudianteInfo, q: str) -> bool:
        matches_codigo = q in (est_info.codigo or "").lower()
        matches_documento = q in (est_info.documento or "").lower()
        matches_nombres = q in (est_info.nombres or "").lower()
        matches_apellidos = q in (est_info.apellidos or "").lower()
        return matches_codigo or matches_documento or matches_nombres or matches_apellidos

    def crear(self, data: RegistroCasoCreate, usuario_id: str, usuario_nombre: str) -> RegistroCasoResponse:
        tipo_enum = TipoRegistroCaso(data.tipo)
        
        nuevo_registro = RegistroCasoEspecial(
            estudiante_id=UUID(data.estudiante_id),
            tipo=tipo_enum,
            estado=EstadoRegistroCaso.ACTIVO,
            observaciones=data.observaciones,
            responsable_id=UUID(usuario_id),
            responsable_nombre=usuario_nombre
        )
        
        self.db.add(nuevo_registro)
        self.db.flush()
        
        historial = HistorialRegistro(
            registro_id=nuevo_registro.id,
            accion=AccionHistorial.APERTURA.value,
            observaciones=data.observaciones or "Creación del registro de caso especial",
            responsable_id=UUID(usuario_id),
            responsable_nombre=usuario_nombre
        )
        self.db.add(historial)
        self.db.commit()
        self.db.refresh(nuevo_registro)
        
        return self._registro_to_response(nuevo_registro)

    def obtener(self, registro_id: str) -> Optional[RegistroCasoResponse]:
        registro = self.db.query(RegistroCasoEspecial).filter(
            RegistroCasoEspecial.id == UUID(registro_id)
        ).first()
        
        if not registro:
            return None
        
        return self._registro_to_response(registro)

    def actualizar(self, registro_id: str, data: RegistroCasoUpdate, usuario_id: str, usuario_nombre: str) -> Optional[RegistroCasoResponse]:
        registro = self.db.query(RegistroCasoEspecial).filter(
            RegistroCasoEspecial.id == UUID(registro_id)
        ).first()
        
        if not registro:
            return None
        
        old_estado = registro.estado.value if hasattr(registro.estado, 'value') else str(registro.estado)
        
        if data.tipo:
            registro.tipo = TipoRegistroCaso(data.tipo)
        if data.estado:
            registro.estado = EstadoRegistroCaso(data.estado)
        if data.observaciones is not None:
            registro.observaciones = data.observaciones
        
        self.db.flush()
        
        new_estado = registro.estado.value if hasattr(registro.estado, 'value') else str(registro.estado)
        
        if old_estado != new_estado:
            accion = AccionHistorial.SEGUIMIENTO.value
            if new_estado == "CERRADO":
                accion = AccionHistorial.CIERRE.value
            elif old_estado == "CERRADO" and new_estado == "ACTIVO":
                accion = AccionHistorial.REAPERTURA.value
            
            historial = HistorialRegistro(
                registro_id=registro.id,
                accion=accion,
                observaciones=data.observaciones or f"Cambio de estado: {old_estado} -> {new_estado}",
                responsable_id=UUID(usuario_id),
                responsable_nombre=usuario_nombre
            )
            self.db.add(historial)
        
        self.db.commit()
        self.db.refresh(registro)
        
        return self._registro_to_response(registro)

    def agregar_historial(self, registro_id: str, accion: str, observaciones: Optional[str], usuario_id: str, usuario_nombre: str) -> Optional[RegistroCasoResponse]:
        registro = self.db.query(RegistroCasoEspecial).filter(
            RegistroCasoEspecial.id == UUID(registro_id)
        ).first()
        
        if not registro:
            return None
        
        historial = HistorialRegistro(
            registro_id=registro.id,
            accion=accion.upper(),
            observaciones=observaciones,
            responsable_id=UUID(usuario_id),
            responsable_nombre=usuario_nombre
        )
        self.db.add(historial)
        self.db.commit()
        
        return self._registro_to_response(registro)
    
    def eliminar(self, registro_id: str) -> bool:
        registro = self.db.query(RegistroCasoEspecial).filter(
            RegistroCasoEspecial.id == UUID(registro_id)
        ).first()
        
        if not registro:
            return False
        
        self.db.delete(registro)
        self.db.commit()
        
        return True

    def listar(self, pagina: int = 1, por_pagina: int = 20, estado: Optional[str] = None, tipo: Optional[str] = None) -> Tuple[List[RegistroCasoResponse], int]:
        query = self.db.query(RegistroCasoEspecial)
        
        if estado:
            query = query.filter(RegistroCasoEspecial.estado == EstadoRegistroCaso(estado))
        if tipo:
            query = query.filter(RegistroCasoEspecial.tipo == TipoRegistroCaso(tipo))
        
        total = query.count()
        registros = query.order_by(RegistroCasoEspecial.created_at.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina).all()
        
        return [self._registro_to_response(r) for r in registros], total

    def obtener_historial(self, registro_id: str) -> List:
        historiales = self.db.query(HistorialRegistro).filter(
            HistorialRegistro.registro_id == UUID(registro_id)
        ).order_by(HistorialRegistro.created_at.asc()).all()
        
        return [
            {
                "id": str(h.id),
                "registro_id": str(h.registro_id),
                "accion": h.accion,
                "observaciones": h.observaciones,
                "responsable_id": str(h.responsable_id),
                "responsable_nombre": h.responsable_nombre,
                "created_at": h.created_at
            }
            for h in historiales
        ]