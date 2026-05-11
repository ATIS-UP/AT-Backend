"""service layer for student operations"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.estudiante import Estudiante, Inscripcion
from app.schemas.estudiante import (
    EstudianteCreate,
    EstudianteUpdate,
    EstudianteResponse,
    HistorialAcademico,
    InscripcionResponse,
)
from app.utils.security import encrypt_data, decrypt_data, sanitize_like_param
from app.utils.audit import AuditService
from app.exceptions import EntityNotFoundError, DuplicateEntityError


class EstudianteService:
    """encapsulates business logic for student crud operations"""

    def __init__(self, db: Session):
        self.db = db

    def _to_response(self, est: Estudiante) -> EstudianteResponse:
        """convert a student model instance to response schema with decryption"""
        return EstudianteResponse(
            id=str(est.id),
            codigo=est.codigo,
            nombres=decrypt_data(est.nombres),
            apellidos=decrypt_data(est.apellidos),
            email=decrypt_data(est.email) if est.email else None,
            documento=decrypt_data(est.documento) if est.documento else None,
            telefono=decrypt_data(est.telefono) if est.telefono else None,
            programa=est.programa,
            semestre=est.semestre,
            promedio_general=(
                float(decrypt_data(str(est.promedio_general)))
                if est.promedio_general
                else None
            ),
            promedio_acumulado=(
                float(decrypt_data(str(est.promedio_acumulado)))
                if est.promedio_acumulado
                else None
            ),
            estado=est.estado.value,
            created_at=est.created_at,
            updated_at=est.updated_at,
        )

    def listar(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        buscar: Optional[str] = None,
        estado: Optional[str] = None,
        programa: Optional[str] = None,
    ) -> tuple[list[EstudianteResponse], int]:
        """query students with filters, decrypt data, return results and total"""
        query = self.db.query(Estudiante)

        if buscar:
            safe_buscar = sanitize_like_param(buscar)
            query = query.filter(
                (Estudiante.codigo.ilike(f"%{safe_buscar}%"))
                | (Estudiante.nombres.ilike(f"%{safe_buscar}%"))
                | (Estudiante.apellidos.ilike(f"%{safe_buscar}%"))
            )
        if estado:
            query = query.filter(Estudiante.estado == estado)
        if programa:
            safe_programa = sanitize_like_param(programa)
            query = query.filter(Estudiante.programa.ilike(f"%{safe_programa}%"))

        total = query.count()

        estudiantes = (
            query.order_by(Estudiante.apellidos)
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
            .all()
        )

        resultados = [self._to_response(est) for est in estudiantes]
        return resultados, total

    def obtener(self, estudiante_id: str) -> EstudianteResponse:
        """get a single student by id, raises EntityNotFoundError if not found"""
        est = (
            self.db.query(Estudiante)
            .filter(Estudiante.id == estudiante_id)
            .first()
        )
        if not est:
            raise EntityNotFoundError("Estudiante", estudiante_id)
        return self._to_response(est)

    def crear(
        self, data: EstudianteCreate, usuario_id: str, ip: str
    ) -> EstudianteResponse:
        """create a student with encrypted fields and audit log"""
        existente = (
            self.db.query(Estudiante)
            .filter(Estudiante.codigo == data.codigo)
            .first()
        )
        if existente:
            raise DuplicateEntityError("Estudiante", "codigo", data.codigo)

        nuevo = Estudiante(
            codigo=data.codigo,
            nombres=encrypt_data(data.nombres),
            apellidos=encrypt_data(data.apellidos),
            email=encrypt_data(data.email) if data.email else None,
            documento=encrypt_data(data.documento) if data.documento else None,
            telefono=encrypt_data(data.telefono) if data.telefono else None,
            programa=data.programa,
            semestre=data.semestre,
            promedio_general=(
                encrypt_data(str(data.promedio_general))
                if data.promedio_general
                else None
            ),
            promedio_acumulado=(
                encrypt_data(str(data.promedio_acumulado))
                if data.promedio_acumulado
                else None
            ),
            estado=data.estado,
        )

        self.db.add(nuevo)
        self.db.commit()
        self.db.refresh(nuevo)

        AuditService.log_crear(
            self.db,
            usuario_id,
            "Estudiante",
            str(nuevo.id),
            {"codigo": nuevo.codigo, "nombres": decrypt_data(nuevo.nombres)},
            ip,
        )

        return self._to_response(nuevo)

    def actualizar(
        self,
        estudiante_id: str,
        data: EstudianteUpdate,
        usuario_id: str,
        ip: str,
    ) -> EstudianteResponse:
        """update student fields with encryption and audit log"""
        est = (
            self.db.query(Estudiante)
            .filter(Estudiante.id == estudiante_id)
            .first()
        )
        if not est:
            raise EntityNotFoundError("Estudiante", estudiante_id)

        datos_anteriores = {
            "nombres": decrypt_data(est.nombres),
            "apellidos": decrypt_data(est.apellidos),
            "programa": est.programa,
        }

        # encrypted fields that need special handling
        encrypted_text_fields = {"nombres", "apellidos", "email", "documento", "telefono"}
        encrypted_numeric_fields = {"promedio_general", "promedio_acumulado"}

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                if key in encrypted_text_fields:
                    setattr(est, key, encrypt_data(value))
                elif key in encrypted_numeric_fields:
                    setattr(est, key, encrypt_data(str(value)))
                else:
                    setattr(est, key, value)

        self.db.commit()
        self.db.refresh(est)

        AuditService.log_actualizar(
            self.db,
            usuario_id,
            "Estudiante",
            str(est.id),
            datos_anteriores,
            update_data,
            ip,
        )

        return self._to_response(est)

    def eliminar(self, estudiante_id: str, usuario_id: str, ip: str) -> None:
        """delete a student and log the action"""
        est = (
            self.db.query(Estudiante)
            .filter(Estudiante.id == estudiante_id)
            .first()
        )
        if not est:
            raise EntityNotFoundError("Estudiante", estudiante_id)

        datos_eliminados = {
            "codigo": est.codigo,
            "nombres": decrypt_data(est.nombres),
        }

        self.db.delete(est)
        self.db.commit()

        AuditService.log_eliminar(
            self.db,
            usuario_id,
            "Estudiante",
            estudiante_id,
            datos_eliminados,
            ip,
        )

    def obtener_historial(self, estudiante_id: str) -> HistorialAcademico:
        """get academic history for a student including inscriptions"""
        est = (
            self.db.query(Estudiante)
            .filter(Estudiante.id == estudiante_id)
            .first()
        )
        if not est:
            raise EntityNotFoundError("Estudiante", estudiante_id)

        inscripciones = (
            self.db.query(Inscripcion)
            .filter(Inscripcion.estudiante_id == estudiante_id)
            .all()
        )

        return HistorialAcademico(
            estudiante=self._to_response(est),
            inscripciones=[
                InscripcionResponse(
                    id=str(ins.id),
                    estudiante_id=str(ins.estudiante_id),
                    materia_id=str(ins.materia_id),
                    materia=None,
                    periodo=ins.periodo,
                    nota_final=(
                        float(decrypt_data(str(ins.nota_final)))
                        if ins.nota_final
                        else None
                    ),
                    estado=ins.estado.value,
                )
                for ins in inscripciones
            ],
            promedio_general=(
                float(decrypt_data(str(est.promedio_general)))
                if est.promedio_general
                else None
            ),
        )
