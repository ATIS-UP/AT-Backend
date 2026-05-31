"""service layer for survey (encuesta) management."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError
from app.models.alerta import Encuesta, RespuestaEncuesta
from app.models.estudiante import Estudiante, EstadoEstudiante
from app.utils.security import decrypt_data
from app.utils.audit import AuditService


class EncuestaService:
    """handles crud, publishing, response collection, and result aggregation for surveys."""

    def __init__(self, db: Session):
        self.db = db

    def listar(self, pagina: int, por_pagina: int, estado: Optional[str] = None) -> tuple[list, int]:
        """list surveys with pagination and optional state filter."""
        query = self.db.query(Encuesta)

        if estado:
            query = query.filter(Encuesta.estado == estado)

        total = query.count()
        encuestas = (
            query.order_by(Encuesta.created_at.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
            .all()
        )

        return [self._to_dict(e) for e in encuestas], total

    def obtener(self, encuesta_id: str) -> dict:
        """get a survey by id, raises EntityNotFoundError if not found."""
        encuesta = self._get_or_raise(encuesta_id)
        return self._to_dict(encuesta)

    def crear(self, data: dict, usuario_id: str) -> dict:
        """create a new survey with questions stored as json."""
        preguntas = data.get("preguntas", [])
        # auto-assign sequential ids to questions that arrive without one
        for i, p in enumerate(preguntas):
            if p.get("id") is None:
                p["id"] = i + 1
        self._validar_preguntas(preguntas)

        encuesta = Encuesta(
            id=uuid.uuid4(),
            titulo=data["titulo"],
            descripcion=data.get("descripcion"),
            preguntas=preguntas,
            estado="BORRADOR",
            periodo=data.get("periodo"),
        )

        self.db.add(encuesta)
        self.db.commit()
        self.db.refresh(encuesta)

        AuditService.log_crear(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Encuesta",
            entidad_id=str(encuesta.id),
            datos={"titulo": encuesta.titulo, "num_preguntas": len(preguntas)},
        )

        return self._to_dict(encuesta)

    def actualizar(self, encuesta_id: str, data: dict, usuario_id: str) -> dict:
        """update a survey. only allowed when in BORRADOR state."""
        encuesta = self._get_or_raise(encuesta_id)

        if encuesta.estado != "BORRADOR":
            raise ValidationError(
                "Solo se pueden editar encuestas en estado BORRADOR"
            )

        datos_anteriores = self._to_dict(encuesta)

        if "titulo" in data:
            encuesta.titulo = data["titulo"]
        if "descripcion" in data:
            encuesta.descripcion = data["descripcion"]
        if "preguntas" in data:
            preguntas = data["preguntas"]
            for i, p in enumerate(preguntas):
                if p.get("id") is None:
                    p["id"] = i + 1
            self._validar_preguntas(preguntas)
            encuesta.preguntas = preguntas
        if "periodo" in data:
            encuesta.periodo = data["periodo"]

        self.db.commit()
        self.db.refresh(encuesta)

        AuditService.log_actualizar(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Encuesta",
            entidad_id=str(encuesta.id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=self._to_dict(encuesta),
        )

        return self._to_dict(encuesta)

    def eliminar(self, encuesta_id: str, usuario_id: str) -> None:
        """delete a survey and its responses."""
        encuesta = self._get_or_raise(encuesta_id)
        datos_eliminados = self._to_dict(encuesta)

        self.db.delete(encuesta)
        self.db.commit()

        AuditService.log_eliminar(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Encuesta",
            entidad_id=str(encuesta.id),
            datos_eliminados=datos_eliminados,
        )

    def publicar(self, encuesta_id: str, usuario_id: str) -> dict:
        """publish a survey: transition from BORRADOR to PUBLICADA.
        requires at least one question."""
        encuesta = self._get_or_raise(encuesta_id)

        if encuesta.estado != "BORRADOR":
            raise ValidationError(
                "Solo se pueden publicar encuestas en estado BORRADOR"
            )

        preguntas = encuesta.preguntas or []
        if len(preguntas) < 1:
            raise ValidationError(
                "La encuesta debe tener al menos una pregunta para ser publicada"
            )

        encuesta.estado = "PUBLICADA"
        encuesta.fecha_inicio = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(encuesta)

        AuditService.log_actualizar(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Encuesta",
            entidad_id=str(encuesta.id),
            datos_anteriores={"estado": "BORRADOR"},
            datos_nuevos={"estado": "PUBLICADA"},
        )

        return self._to_dict(encuesta)

    def cerrar(self, encuesta_id: str, usuario_id: str) -> dict:
        """close a survey: transition to CERRADA state."""
        encuesta = self._get_or_raise(encuesta_id)

        if encuesta.estado != "PUBLICADA":
            raise ValidationError(
                "Solo se pueden cerrar encuestas en estado PUBLICADA"
            )

        encuesta.estado = "CERRADA"
        encuesta.fecha_fin = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(encuesta)

        AuditService.log_actualizar(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Encuesta",
            entidad_id=str(encuesta.id),
            datos_anteriores={"estado": "PUBLICADA"},
            datos_nuevos={"estado": "CERRADA"},
        )

        return self._to_dict(encuesta)

    def registrar_respuesta(
        self, encuesta_id: str, estudiante_id: str, respuestas: list
    ) -> dict:
        """save a student response to a published survey.
        rejects if survey is not PUBLICADA, student not ACTIVO, or already responded."""
        encuesta = self._get_or_raise(encuesta_id)

        if encuesta.estado != "PUBLICADA":
            raise ValidationError(
                "Solo se pueden responder encuestas en estado PUBLICADA"
            )

        # validate student exists and is active
        estudiante = self.db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
        if not estudiante:
            raise EntityNotFoundError("Estudiante", estudiante_id)
        if estudiante.estado != EstadoEstudiante.ACTIVO:
            raise ValidationError(f"Los estudiantes en estado {estudiante.estado.value} no pueden responder encuestas")

        # check for duplicate response
        existing = (
            self.db.query(RespuestaEncuesta)
            .filter(
                RespuestaEncuesta.encuesta_id == encuesta.id,
                RespuestaEncuesta.estudiante_id == estudiante_id,
            )
            .first()
        )
        if existing:
            raise DuplicateEntityError(
                entity="RespuestaEncuesta",
                field="estudiante_id",
                value=estudiante_id,
            )

        respuesta = RespuestaEncuesta(
            id=uuid.uuid4(),
            encuesta_id=encuesta.id,
            estudiante_id=estudiante_id,
            respuestas=respuestas,
        )

        self.db.add(respuesta)
        self.db.commit()
        self.db.refresh(respuesta)

        return self._respuesta_to_dict(respuesta)

    def obtener_resultados(self, encuesta_id: str) -> dict:
        """aggregate results for a survey.
        - opcion_multiple: count per option
        - escala_likert: average + distribution
        - texto_libre: list of responses"""
        encuesta = self._get_or_raise(encuesta_id)

        respuestas = (
            self.db.query(RespuestaEncuesta)
            .filter(RespuestaEncuesta.encuesta_id == encuesta.id)
            .all()
        )

        preguntas = encuesta.preguntas or []
        resultados_por_pregunta = []

        for pregunta in preguntas:
            pregunta_id = pregunta.get("id")
            tipo = pregunta.get("tipo", "texto_libre")
            texto = pregunta.get("texto", "")

            # collect answers for this question
            answers = []
            for r in respuestas:
                resp_data = r.respuestas
                if isinstance(resp_data, list):
                    # responses stored as list of {pregunta_id, valor}
                    for item in resp_data:
                        if item.get("pregunta_id") == pregunta_id:
                            answers.append(item.get("valor"))
                            break
                elif isinstance(resp_data, dict):
                    # responses stored as dict {pregunta_id: valor}
                    val = resp_data.get(str(pregunta_id))
                    if val is not None:
                        answers.append(val)

            resultado = {
                "pregunta_id": pregunta_id,
                "texto": texto,
                "tipo": tipo,
                "total_respuestas": len(answers),
            }

            if tipo == "opcion_multiple":
                distribucion = {}
                for a in answers:
                    if isinstance(a, str):
                        distribucion[a] = distribucion.get(a, 0) + 1
                    elif isinstance(a, list):
                        for opt in a:
                            distribucion[opt] = distribucion.get(opt, 0) + 1
                resultado["distribucion"] = distribucion
                resultado["promedio"] = None

            elif tipo == "escala_likert":
                numeric_vals = []
                for a in answers:
                    try:
                        numeric_vals.append(float(a))
                    except (TypeError, ValueError):
                        continue
                promedio = (
                    sum(numeric_vals) / len(numeric_vals) if numeric_vals else None
                )
                distribucion = {}
                for v in numeric_vals:
                    key = str(int(v))
                    distribucion[key] = distribucion.get(key, 0) + 1
                resultado["promedio"] = promedio
                resultado["distribucion"] = distribucion

            elif tipo == "texto_libre":
                resultado["respuestas_texto"] = answers
                resultado["distribucion"] = None
                resultado["promedio"] = None

            else:
                resultado["distribucion"] = None
                resultado["promedio"] = None

            resultados_por_pregunta.append(resultado)

        return {
            "encuesta_id": str(encuesta.id),
            "titulo": encuesta.titulo,
            "total_respuestas": len(respuestas),
            "resultados_por_pregunta": resultados_por_pregunta,
        }

    def listar_publicas(self) -> list[dict]:
        """list surveys in PUBLICADA state (no auth required)."""
        encuestas = (
            self.db.query(Encuesta)
            .filter(Encuesta.estado == "PUBLICADA")
            .order_by(Encuesta.created_at.desc())
            .all()
        )
        return [self._to_dict(e) for e in encuestas]

    def obtener_info_publica(self, encuesta_id: str) -> dict:
        """get public survey info (no auth required). only for PUBLICADA surveys."""
        encuesta = self._get_or_raise(encuesta_id)
        if encuesta.estado != "PUBLICADA":
            raise ValidationError("La encuesta no esta disponible")
        return {
            "id": str(encuesta.id),
            "titulo": encuesta.titulo,
            "descripcion": encuesta.descripcion,
            "preguntas": encuesta.preguntas or [],
        }

    def verificar_estudiante(
        self, encuesta_id: str, documento: str
    ) -> dict:
        """verify a student by documento and check if they can answer.
        documento is encrypted, so we decrypt and compare in Python."""
        encuesta = self._get_or_raise(encuesta_id)

        if encuesta.estado != "PUBLICADA":
            raise ValidationError("La encuesta no esta disponible para responder")

        # find student by decrypted documento
        estudiante = None
        all_students = self.db.query(Estudiante).all()
        for est in all_students:
            if not est.documento:
                continue
            decrypted = decrypt_data(est.documento)
            if decrypted == documento:
                estudiante = est
                break

        if not estudiante:
            return {
                "existe": False,
                "ya_respondio": False,
                "puede_responder": False,
                "estudiante_nombre": None,
                "estudiante_id": None,
            }

        nombres = decrypt_data(estudiante.nombres)
        apellidos = decrypt_data(estudiante.apellidos)
        estudiante_nombre = f"{nombres} {apellidos}".strip()

        if estudiante.estado != EstadoEstudiante.ACTIVO:
            return {
                "existe": True,
                "ya_respondio": False,
                "puede_responder": False,
                "estudiante_nombre": estudiante_nombre,
                "estudiante_id": str(estudiante.id),
            }

        # check for existing response
        existing = (
            self.db.query(RespuestaEncuesta)
            .filter(
                RespuestaEncuesta.encuesta_id == encuesta.id,
                RespuestaEncuesta.estudiante_id == estudiante.id,
            )
            .first()
        )

        return {
            "existe": True,
            "ya_respondio": existing is not None,
            "puede_responder": existing is None and estudiante.estado == EstadoEstudiante.ACTIVO,
            "estudiante_nombre": estudiante_nombre,
            "estudiante_id": str(estudiante.id),
        }

    def responder_publico(
        self, encuesta_id: str, documento: str, respuestas: list
    ) -> dict:
        """submit survey answers as a public student (no auth token needed).
        verifies documento matches a registered student."""
        verificado = self.verificar_estudiante(encuesta_id, documento)
        if not verificado["puede_responder"]:
            if not verificado["existe"]:
                raise ValidationError("El documento no coincide con el sistema")
            if verificado["ya_respondio"]:
                raise ValidationError("Ya has respondido esta encuesta")
            raise ValidationError("No puedes responder esta encuesta")

        estudiante_id = verificado["estudiante_id"]
        # reuse existing registration logic
        return self.registrar_respuesta(encuesta_id, estudiante_id, respuestas)

    # -- private helpers --

    def _get_or_raise(self, encuesta_id: str) -> Encuesta:
        """fetch encuesta by id or raise EntityNotFoundError."""
        encuesta = (
            self.db.query(Encuesta)
            .filter(Encuesta.id == encuesta_id)
            .first()
        )
        if not encuesta:
            raise EntityNotFoundError("Encuesta", encuesta_id)
        return encuesta

    def _validar_preguntas(self, preguntas: list) -> None:
        """validate question structure and types."""
        tipos_validos = {"opcion_multiple", "texto_libre", "escala_likert", "ABIERTA"}

        for i, pregunta in enumerate(preguntas):
            if not isinstance(pregunta, dict):
                raise ValidationError(
                    f"La pregunta en posicion {i} debe ser un objeto"
                )
            if "texto" not in pregunta:
                raise ValidationError(
                    f"La pregunta en posicion {i} debe tener un campo 'texto'"
                )
            tipo = pregunta.get("tipo", "texto_libre")
            if tipo not in tipos_validos:
                raise ValidationError(
                    f"Tipo de pregunta invalido: '{tipo}'. "
                    f"Tipos validos: {', '.join(sorted(tipos_validos))}"
                )
            if tipo == "opcion_multiple":
                opciones = pregunta.get("opciones")
                if not opciones or not isinstance(opciones, list) or len(opciones) < 2:
                    raise ValidationError(
                        f"La pregunta en posicion {i} de tipo opcion_multiple "
                        "debe tener al menos 2 opciones"
                    )

    def _to_dict(self, encuesta: Encuesta) -> dict:
        """convert encuesta model to dictionary."""
        return {
            "id": str(encuesta.id),
            "titulo": encuesta.titulo,
            "descripcion": encuesta.descripcion,
            "preguntas": encuesta.preguntas or [],
            "estado": encuesta.estado,
            "periodo": encuesta.periodo,
            "fecha_inicio": (
                encuesta.fecha_inicio.isoformat() if encuesta.fecha_inicio else None
            ),
            "fecha_fin": (
                encuesta.fecha_fin.isoformat() if encuesta.fecha_fin else None
            ),
            "es_publica": encuesta.es_publica,
            "created_at": (
                encuesta.created_at.isoformat() if encuesta.created_at else None
            ),
            "updated_at": (
                encuesta.updated_at.isoformat() if encuesta.updated_at else None
            ),
        }

    def _respuesta_to_dict(self, respuesta: RespuestaEncuesta) -> dict:
        """convert respuesta model to dictionary."""
        return {
            "id": str(respuesta.id),
            "encuesta_id": str(respuesta.encuesta_id),
            "estudiante_id": str(respuesta.estudiante_id),
            "respuestas": respuesta.respuestas,
            "created_at": (
                respuesta.created_at.isoformat() if respuesta.created_at else None
            ),
        }
