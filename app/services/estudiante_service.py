"""service layer for student operations"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.estudiante import Estudiante, Inscripcion, EstadoEstudiante
from app.models.alerta import Alerta, RespuestaEncuesta, Artefacto
from app.models.caso_especial import RegistroCasoEspecial
from app.schemas.estudiante import (
    EstudianteCreate,
    EstudianteUpdate,
    EstudianteResponse,
    EstudianteRelacionesConteo,
    HistorialAcademico,
    InscripcionResponse,
)
from app.utils.security import encrypt_data, decrypt_data, sanitize_like_param
from app.utils.audit import AuditService
from app.exceptions import EntityNotFoundError, DuplicateEntityError, ValidationError
from itertools import chain


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
            fecha_nacimiento=est.fecha_nacimiento,
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
        """query students with filters, decrypt data, return results and total.
        Note: nombres/apellidos are encrypted, so ilike cannot match them at DB level.
        For name searches, we decrypt and filter in Python."""
        query = self.db.query(Estudiante)

        if estado:
            query = query.filter(Estudiante.estado == estado)
        if programa:
            safe_programa = sanitize_like_param(programa)
            query = query.filter(Estudiante.programa.ilike(f"%{safe_programa}%"))

        if buscar:
            safe_buscar = sanitize_like_param(buscar)
            # codigo is unencrypted — ilike works at DB level
            codigo_filter = Estudiante.codigo.ilike(f"%{safe_buscar}%")

            # gather ids matching by codigo
            codigo_ids = {est.id for est in query.filter(codigo_filter).all()}

            # decrypt and filter by name for remaining students
            all_ests = query.all()
            for est in all_ests:
                if est.id in codigo_ids:
                    continue
                nombres = decrypt_data(est.nombres)
                apellidos = decrypt_data(est.apellidos)
                if safe_buscar.lower() in (nombres or '').lower() or safe_buscar.lower() in (apellidos or '').lower():
                    codigo_ids.add(est.id)

            if codigo_ids:
                query = query.filter(Estudiante.id.in_(list(codigo_ids)))
            else:
                # no matches — return empty
                return [], 0

        total = query.count()

        estudiantes = (
            query.order_by(Estudiante.codigo)
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

    def buscar_por_codigo(self, codigo: str) -> Optional[EstudianteResponse]:
        """look up a student by their codigo (unencrypted). returns None if not found."""
        est = (
            self.db.query(Estudiante)
            .filter(Estudiante.codigo == codigo)
            .first()
        )
        if not est:
            return None
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
            fecha_nacimiento=data.fecha_nacimiento,
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

    def obtener_conteo_relaciones(self, estudiante_id: str) -> EstudianteRelacionesConteo:
        """count all related records for a student (alerts, cases, enrollments, etc)"""
        est_id = estudiante_id
        return EstudianteRelacionesConteo(
            alertas=self.db.query(Alerta).filter(Alerta.estudiante_id == est_id).count(),
            casos=self.db.query(RegistroCasoEspecial).filter(RegistroCasoEspecial.estudiante_id == est_id).count(),
            inscripciones=self.db.query(Inscripcion).filter(Inscripcion.estudiante_id == est_id).count(),
            respuestas_encuestas=self.db.query(RespuestaEncuesta).filter(RespuestaEncuesta.estudiante_id == est_id).count(),
            artefactos=self.db.query(Artefacto).filter(Artefacto.estudiante_id == est_id).count(),
        )

    def cambiar_estado(self, estudiante_id: str, nuevo_estado: str, usuario_id: str, ip: str) -> EstudianteResponse:
        """change student estado (for inactivating/activating students)"""
        est = (
            self.db.query(Estudiante)
            .filter(Estudiante.id == estudiante_id)
            .first()
        )
        if not est:
            raise EntityNotFoundError("Estudiante", estudiante_id)

        estado_anterior = est.estado.value if hasattr(est.estado, 'value') else str(est.estado)

        try:
            est.estado = EstadoEstudiante(nuevo_estado)
        except ValueError:
            raise ValidationError(f"Estado inválido: {nuevo_estado}. Valores permitidos: {', '.join([e.value for e in EstadoEstudiante])}")

        self.db.commit()
        self.db.refresh(est)

        AuditService.log_actualizar(
            self.db,
            usuario_id,
            "Estudiante",
            str(est.id),
            {"estado": estado_anterior},
            {"estado": nuevo_estado},
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
