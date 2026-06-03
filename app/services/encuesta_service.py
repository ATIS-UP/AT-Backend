"""service layer for survey (encuesta) management."""
import uuid
from datetime import datetime
from datetime import UTC as tz_utc
from typing import Optional

from sqlalchemy.orm import Session

from app.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError
from app.models.alerta import Encuesta, RespuestaEncuesta
from app.models.estudiante import Estudiante, EstadoEstudiante
from app.utils.security import decrypt_data, encrypt_data
from app.utils.audit import AuditService


CAMPO_ATTR_MAP = {
    "email": ("email", True),
    "telefono": ("telefono", True),
    "programa": ("programa", False),
    "semestre": ("semestre", False),
    "estrato": ("estrato", False),
    "procedencia": ("procedencia", False),
    "genero": ("genero", False),
    "ingreso_familiar": ("ingreso_familiar", False),
}

CAMPO_VALIDACION = {
    "estrato": lambda v: 1 <= int(v) <= 6,
    "genero": lambda v: str(v) in ("H", "M", "OTRO"),
    "procedencia": lambda v: str(v) in ("LOCAL", "FORANEO"),
    "semestre": lambda v: 1 <= int(v) <= 12,
    "email": lambda v: "@" in str(v) and len(str(v)) <= 255,
    "telefono": lambda v: str(v).isdigit() and 7 <= len(str(v)) <= 15,
    "ingreso_familiar": lambda v: int(v) > 0,
    "programa": lambda v: len(str(v)) <= 255,
}

CAMPO_ERROR_MSG = {
    "estrato": "Debe seleccionar un estrato válido (1 a 6)",
    "genero": "Debe seleccionar un género válido (H, M u OTRO)",
    "procedencia": "Debe seleccionar una procedencia válida (LOCAL o FORANEO)",
    "semestre": "Semestre debe ser un número entre 1 y 12",
    "email": "El correo electrónico no es válido",
    "telefono": "El teléfono solo debe contener dígitos (7 a 15 caracteres)",
    "ingreso_familiar": "El ingreso familiar debe ser un número entero positivo",
    "programa": "El programa académico excede la longitud máxima",
}


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

        fecha_fin = data.get("fecha_fin")
        if isinstance(fecha_fin, str):
            fecha_fin = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))

        encuesta = Encuesta(
            id=uuid.uuid4(),
            titulo=data["titulo"],
            descripcion=data.get("descripcion"),
            preguntas=preguntas,
            estado="BORRADOR",
            periodo=data.get("periodo"),
            fecha_fin=fecha_fin,
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
        """update a survey. only allowed when in BORRADOR state.
        fecha_fin can also be set/updated while PUBLICADA (used as auto-close deadline)."""
        encuesta = self._get_or_raise(encuesta_id)

        if encuesta.estado not in ("BORRADOR", "PUBLICADA"):
            raise ValidationError(
                "Solo se pueden editar encuestas en estado BORRADOR o PUBLICADA"
            )

        datos_anteriores = self._to_dict(encuesta)

        if encuesta.estado == "BORRADOR":
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

        if "fecha_fin" in data:
            fecha_fin = data["fecha_fin"]
            if fecha_fin is None:
                encuesta.fecha_fin = None
            elif isinstance(fecha_fin, str):
                encuesta.fecha_fin = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            else:
                encuesta.fecha_fin = fecha_fin

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

    def procesar_vencimientos(self) -> dict:
        """close any PUBLICADA surveys whose fecha_fin has passed.
        returns counts of surveys closed vs total processed."""
        ahora = datetime.now(tz_utc)

        candidatas = (
            self.db.query(Encuesta)
            .filter(
                Encuesta.estado == "PUBLICADA",
                Encuesta.fecha_fin.isnot(None),
                Encuesta.fecha_fin <= ahora,
            )
            .all()
        )

        procesadas = len(candidatas)
        cerradas = 0

        for encuesta in candidatas:
            datos_anteriores = {
                "estado": encuesta.estado,
                "fecha_fin": (
                    encuesta.fecha_fin.isoformat() if encuesta.fecha_fin else None
                ),
            }
            encuesta.estado = "CERRADA"
            cerradas += 1

            AuditService.log_actualizar(
                db=self.db,
                usuario_id=None,
                entidad="Encuesta",
                entidad_id=str(encuesta.id),
                datos_anteriores=datos_anteriores,
                datos_nuevos={"estado": "CERRADA", "motivo": "vencimiento_fecha_fin"},
            )

        self.db.commit()

        return {
            "cerradas": cerradas,
            "procesadas": procesadas,
            "fecha_referencia": ahora.isoformat(),
        }

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

    def duplicar(self, encuesta_id: str, usuario_id: str) -> dict:
        """clone a PUBLISHED or CLOSED survey as a new BORRADOR.
        copies titulo + descripcion + preguntas (with options) + periodo.
        resets estado to BORRADOR, clears fechas, does NOT copy responses."""
        original = self._get_or_raise(encuesta_id)

        if original.estado not in ("PUBLICADA", "CERRADA"):
            raise ValidationError(
                "Solo se pueden duplicar encuestas en estado PUBLICADA o CERRADA"
            )

        preguntas_originales = original.preguntas or []
        nuevas_preguntas = [
            {**p, "id": i + 1}
            for i, p in enumerate(preguntas_originales)
        ]

        clon = Encuesta(
            id=uuid.uuid4(),
            titulo=f"{original.titulo} (copia)",
            descripcion=original.descripcion,
            preguntas=nuevas_preguntas,
            estado="BORRADOR",
            periodo=original.periodo,
            fecha_inicio=None,
            fecha_fin=None,
            es_publica=False,
        )

        self.db.add(clon)
        self.db.commit()
        self.db.refresh(clon)

        AuditService.log_crear(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Encuesta",
            entidad_id=str(clon.id),
            datos={
                "titulo": clon.titulo,
                "num_preguntas": len(nuevas_preguntas),
                "duplicado_de": str(original.id),
            },
        )

        return self._to_dict(clon)

    def crear_plantilla_datos(self, usuario_id: str) -> dict:
        preguntas = [
            {"id": 1, "texto": "Estrato socioeconómico", "tipo": "opcion_multiple",
             "opciones": ["1", "2", "3", "4", "5", "6"], "requerida": True, "campo": "estrato", "editable": True},
            {"id": 2, "texto": "Género", "tipo": "opcion_multiple",
             "opciones": ["H", "M", "OTRO"], "requerida": True, "campo": "genero", "editable": True},
            {"id": 3, "texto": "Procedencia", "tipo": "opcion_multiple",
             "opciones": ["LOCAL", "FORANEO"], "requerida": True, "campo": "procedencia", "editable": True},
            {"id": 4, "texto": "Ingreso familiar mensual ($)", "tipo": "texto_libre",
             "requerida": False, "campo": "ingreso_familiar", "editable": True},
            {"id": 5, "texto": "Correo electrónico", "tipo": "texto_libre",
             "requerida": False, "campo": "email", "editable": True},
            {"id": 6, "texto": "Teléfono de contacto", "tipo": "texto_libre",
             "requerida": False, "campo": "telefono", "editable": True},
            {"id": 7, "texto": "Programa académico", "tipo": "texto_libre",
             "requerida": True, "campo": "programa", "editable": False},
            {"id": 8, "texto": "Semestre actual", "tipo": "opcion_multiple",
             "opciones": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
             "requerida": True, "campo": "semestre", "editable": False},
        ]
        encuesta = Encuesta(
            id=uuid.uuid4(),
            titulo="Actualización de Datos Estudiantiles",
            descripcion="Completa o actualiza tus datos personales y académicos para mantener la información al día.",
            preguntas=preguntas,
            estado="BORRADOR",
            periodo=None,
        )
        self.db.add(encuesta)
        self.db.commit()
        self.db.refresh(encuesta)

        AuditService.log_crear(
            db=self.db,
            usuario_id=usuario_id,
            entidad="Encuesta",
            entidad_id=str(encuesta.id),
            datos={"titulo": encuesta.titulo, "num_preguntas": len(preguntas), "es_plantilla": True},
        )

        return self._to_dict(encuesta)

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
        encuesta.fecha_inicio = datetime.now(tz_utc)

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
        encuesta.fecha_fin = datetime.now(tz_utc)

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
            "preguntas": (
                self._preparar_preguntas_con_datos(encuesta, estudiante)
                if existing is None and estudiante.estado == EstadoEstudiante.ACTIVO
                else None
            ),
        }

    def responder_publico(
        self, encuesta_id: str, documento: str, respuestas: list
    ) -> dict:
        """submit survey answers as a public student (no auth token needed).
        verifies documento matches a registered student, saves response, and
        updates estudiante fields from mapped questions."""
        verificado = self.verificar_estudiante(encuesta_id, documento)
        if not verificado["puede_responder"]:
            if not verificado["existe"]:
                raise ValidationError("El documento no coincide con el sistema")
            if verificado["ya_respondio"]:
                raise ValidationError("Ya has respondido esta encuesta")
            raise ValidationError("No puedes responder esta encuesta")

        estudiante_id = verificado["estudiante_id"]
        encuesta = self._get_or_raise(encuesta_id)
        estudiante = (
            self.db.query(Estudiante)
            .filter(Estudiante.id == estudiante_id)
            .first()
        )

        # validate campo values BEFORE saving response (prevents lockout on bad data)
        self._validar_respuestas_campo(encuesta, respuestas)

        result = self.registrar_respuesta(encuesta_id, estudiante_id, respuestas)
        self._actualizar_estudiante_desde_respuestas(
            estudiante, encuesta, respuestas
        )
        self.db.commit()

        return result

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

    def _resolver_campo(self, estudiante: Estudiante, campo: str) -> str | None:
        if campo not in CAMPO_ATTR_MAP:
            return None
        attr, encrypted = CAMPO_ATTR_MAP[campo]
        valor = getattr(estudiante, attr, None)
        if valor is None:
            return None
        if encrypted:
            return decrypt_data(valor)
        return str(valor)

    def _enmascarar_valor(self, campo: str, valor: str | None) -> str | None:
        if valor is None:
            return None
        if campo == "email" and "@" in valor:
            local, domain = valor.split("@", 1)
            visible = local[:4] if len(local) >= 4 else local[:1]
            tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
            return f"{visible}****@****.{tld}" if tld else f"{visible}****@****"
        if campo == "telefono":
            visible = valor[-4:] if len(valor) >= 4 else valor
            return f"****{visible}"
        return valor

    def _preparar_preguntas_con_datos(
        self, encuesta: Encuesta, estudiante: Estudiante
    ) -> list[dict]:
        result = []
        for p in (encuesta.preguntas or []):
            p_out = dict(p)
            campo = p_out.get("campo")
            if campo:
                valor = self._resolver_campo(estudiante, campo)
                p_out["valor_actual"] = self._enmascarar_valor(campo, valor)
            else:
                p_out["valor_actual"] = None
            result.append(p_out)
        return result

    def _validar_respuestas_campo(
        self, encuesta: Encuesta, respuestas: list[dict]
    ) -> None:
        preguntas = {p.get("id"): p for p in (encuesta.preguntas or [])}
        for r in respuestas:
            pid = r.get("pregunta_id")
            pregunta = preguntas.get(pid, {})
            campo = pregunta.get("campo")
            editable = pregunta.get("editable", True)
            valor_nuevo = r.get("valor")
            if not campo or not editable:
                continue
            if valor_nuevo is None or (
                isinstance(valor_nuevo, str) and not valor_nuevo.strip()
            ):
                continue
            if campo in CAMPO_VALIDACION:
                try:
                    if not CAMPO_VALIDACION[campo](valor_nuevo):
                        msg = CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'")
                        raise ValidationError(msg)
                except (TypeError, ValueError):
                    msg = CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'")
                    raise ValidationError(msg)

    def _actualizar_estudiante_desde_respuestas(
        self, estudiante: Estudiante, encuesta: Encuesta, respuestas: list[dict]
    ) -> None:
        preguntas = {p.get("id"): p for p in (encuesta.preguntas or [])}
        for r in respuestas:
            pid = r.get("pregunta_id")
            pregunta = preguntas.get(pid, {})
            campo = pregunta.get("campo")
            editable = pregunta.get("editable", True)
            valor_nuevo = r.get("valor")
            if not campo or not editable:
                continue
            if valor_nuevo is None or (
                isinstance(valor_nuevo, str) and not valor_nuevo.strip()
            ):
                continue
            if campo in CAMPO_VALIDACION:
                try:
                    if not CAMPO_VALIDACION[campo](valor_nuevo):
                        msg = CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'")
                        raise ValidationError(msg)
                except (TypeError, ValueError):
                    msg = CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'")
                    raise ValidationError(msg)
            attr, encrypted = CAMPO_ATTR_MAP.get(campo, (None, False))
            if not attr:
                continue
            if encrypted:
                setattr(estudiante, attr, encrypt_data(str(valor_nuevo)))
            elif campo in ("estrato", "semestre", "ingreso_familiar"):
                setattr(estudiante, attr, int(valor_nuevo))
            else:
                setattr(estudiante, attr, str(valor_nuevo))

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
