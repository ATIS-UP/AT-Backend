"""service layer for public survey endpoints (no auth required)."""
import uuid
from datetime import datetime
from datetime import UTC as tz_utc

from sqlalchemy.orm import Session

from app.exceptions import EntityNotFoundError, ValidationError
from app.models.alerta import Encuesta, RespuestaEncuesta
from app.models.estudiante import Estudiante, EstadoEstudiante
from app.utils.security import decrypt_data, encrypt_data, hash_data
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
    "ingreso_familiar": lambda v: str(v) in [r["label"] for r in SMMLV_RANGOS.values()],
    "programa": lambda v: len(str(v)) <= 255,
}

SMMLV_RANGOS = {
    "menos_1": {"label": "Menos de 1 SMMLV ($1.300.000)", "valor_promedio": 650000},
    "entre_1_2": {"label": "Entre 1 y 2 SMMLV ($1.300.000 - $2.600.000)", "valor_promedio": 1950000},
    "entre_2_3": {"label": "Entre 2 y 3 SMMLV ($2.600.000 - $3.900.000)", "valor_promedio": 3250000},
    "entre_3_5": {"label": "Entre 3 y 5 SMMLV ($3.900.000 - $6.500.000)", "valor_promedio": 5200000},
    "mas_5": {"label": "Más de 5 SMMLV (+$6.500.000)", "valor_promedio": 7800000},
}

CAMPO_ERROR_MSG = {
    "estrato": "Debe seleccionar un estrato válido (1 a 6)",
    "genero": "Debe seleccionar un género válido (H, M u OTRO)",
    "procedencia": "Debe seleccionar una procedencia válida (LOCAL o FORANEO)",
    "semestre": "Semestre debe ser un número entre 1 y 12",
    "email": "El correo electrónico no es válido",
    "telefono": "El teléfono solo debe contener dígitos (7 a 15 caracteres)",
    "ingreso_familiar": "Debe seleccionar un rango de ingreso válido",
    "programa": "El programa académico excede la longitud máxima",
}


class EncuestaPublicaService:
    """handles public survey flows: listing, verification, response, and data templates."""

    def __init__(self, db: Session):
        self.db = db

    def listar_publicas(self) -> list[dict]:
        encuestas = (
            self.db.query(Encuesta)
            .filter(Encuesta.estado == "PUBLICADA")
            .order_by(Encuesta.created_at.desc())
            .all()
        )
        return [self._to_dict(e) for e in encuestas]

    def obtener_info_publica(self, encuesta_id: str) -> dict:
        encuesta = self._get_or_raise(encuesta_id)
        if encuesta.estado != "PUBLICADA":
            raise ValidationError("La encuesta no esta disponible")
        return {
            "id": str(encuesta.id),
            "titulo": encuesta.titulo,
            "descripcion": encuesta.descripcion,
            "preguntas": encuesta.preguntas or [],
        }

    def verificar_estudiante(self, encuesta_id: str, documento: str) -> dict:
        encuesta = self._get_or_raise(encuesta_id)
        if encuesta.estado != "PUBLICADA":
            raise ValidationError("La encuesta no esta disponible para responder")

        documento_hash = hash_data(documento.strip())
        estudiante = (
            self.db.query(Estudiante)
            .filter(Estudiante.documento_hash == documento_hash)
            .first()
        )

        # Legacy students without documento_hash are not found by hash lookup.
        # Full-table decryption scans are omitted to prevent DoS; run the
        # hash-backfill migration (populate documento_hash) to cover them.
        if not estudiante:
            return {"existe": False, "ya_respondio": False, "puede_responder": False,
                    "estudiante_nombre": None, "estudiante_id": None}

        nombres = decrypt_data(estudiante.nombres)
        apellidos = decrypt_data(estudiante.apellidos)
        estudiante_nombre = f"{nombres} {apellidos}".strip()

        if estudiante.estado != EstadoEstudiante.ACTIVO:
            return {"existe": True, "ya_respondio": False, "puede_responder": False,
                    "estudiante_nombre": estudiante_nombre, "estudiante_id": str(estudiante.id)}

        existing = (
            self.db.query(RespuestaEncuesta)
            .filter(RespuestaEncuesta.encuesta_id == encuesta.id,
                    RespuestaEncuesta.estudiante_id == estudiante.id)
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

    def responder_publico(self, encuesta_id: str, documento: str, respuestas: list) -> dict:
        from app.services.encuesta_service import EncuestaService
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
            self.db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
        )
        self._validar_respuestas_campo(encuesta, respuestas)

        admin_service = EncuestaService(self.db)
        result = admin_service.registrar_respuesta(encuesta_id, estudiante_id, respuestas)
        self._actualizar_estudiante_desde_respuestas(estudiante, encuesta, respuestas)
        self.db.commit()
        return result

    def crear_plantilla_datos(self, usuario_id: str) -> dict:
        preguntas = [
            {"id": 1, "texto": "Estrato socioeconómico", "tipo": "opcion_multiple",
             "opciones": ["1", "2", "3", "4", "5", "6"], "requerida": True, "campo": "estrato", "editable": True},
            {"id": 2, "texto": "Género", "tipo": "opcion_multiple",
             "opciones": ["H", "M", "OTRO"], "requerida": True, "campo": "genero", "editable": True},
            {"id": 3, "texto": "Procedencia", "tipo": "opcion_multiple",
             "opciones": ["LOCAL", "FORANEO"], "requerida": True, "campo": "procedencia", "editable": True},
            {"id": 4, "texto": "Ingreso familiar mensual (SMMLV)", "tipo": "opcion_multiple",
             "opciones": [r["label"] for r in SMMLV_RANGOS.values()], "requerida": False, "campo": "ingreso_familiar", "editable": True},
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
            preguntas=preguntas, estado="BORRADOR", periodo=None,
        )
        self.db.add(encuesta)
        self.db.flush()
        self.db.refresh(encuesta)
        AuditService.log_crear(
            db=self.db, usuario_id=usuario_id, entidad="Encuesta",
            entidad_id=str(encuesta.id),
            datos={"titulo": encuesta.titulo, "num_preguntas": len(preguntas), "es_plantilla": True},
        )
        self.db.commit()
        return self._to_dict(encuesta)

    # -- private helpers --

    def _get_or_raise(self, encuesta_id: str) -> Encuesta:
        encuesta = self.db.query(Encuesta).filter(Encuesta.id == encuesta_id).first()
        if not encuesta:
            raise EntityNotFoundError("Encuesta", encuesta_id)
        return encuesta

    def _to_dict(self, encuesta: Encuesta) -> dict:
        return {
            "id": str(encuesta.id),
            "titulo": encuesta.titulo,
            "descripcion": encuesta.descripcion,
            "preguntas": encuesta.preguntas or [],
            "estado": encuesta.estado,
            "periodo": encuesta.periodo,
            "fecha_inicio": (encuesta.fecha_inicio.isoformat() if encuesta.fecha_inicio else None),
            "fecha_fin": (encuesta.fecha_fin.isoformat() if encuesta.fecha_fin else None),
            "es_publica": encuesta.es_publica,
            "created_at": (encuesta.created_at.isoformat() if encuesta.created_at else None),
            "updated_at": (encuesta.updated_at.isoformat() if encuesta.updated_at else None),
        }

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

    def _preparar_preguntas_con_datos(self, encuesta: Encuesta, estudiante: Estudiante) -> list[dict]:
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

    def _validar_respuestas_campo(self, encuesta: Encuesta, respuestas: list[dict]) -> None:
        preguntas = {p.get("id"): p for p in (encuesta.preguntas or [])}
        for r in respuestas:
            pid = r.get("pregunta_id")
            pregunta = preguntas.get(pid, {})
            campo = pregunta.get("campo")
            editable = pregunta.get("editable", True)
            valor_nuevo = r.get("valor")
            if not campo or not editable:
                continue
            if valor_nuevo is None or (isinstance(valor_nuevo, str) and not valor_nuevo.strip()):
                continue
            if campo in CAMPO_VALIDACION:
                try:
                    if not CAMPO_VALIDACION[campo](valor_nuevo):
                        raise ValidationError(CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'"))
                except (TypeError, ValueError):
                    raise ValidationError(CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'"))

    def _actualizar_estudiante_desde_respuestas(self, estudiante: Estudiante, encuesta: Encuesta, respuestas: list[dict]) -> None:
        preguntas = {p.get("id"): p for p in (encuesta.preguntas or [])}
        for r in respuestas:
            pid = r.get("pregunta_id")
            pregunta = preguntas.get(pid, {})
            campo = pregunta.get("campo")
            editable = pregunta.get("editable", True)
            valor_nuevo = r.get("valor")
            if not campo or not editable:
                continue
            if valor_nuevo is None or (isinstance(valor_nuevo, str) and not valor_nuevo.strip()):
                continue
            if campo in CAMPO_VALIDACION:
                try:
                    if not CAMPO_VALIDACION[campo](valor_nuevo):
                        raise ValidationError(CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'"))
                except (TypeError, ValueError):
                    raise ValidationError(CAMPO_ERROR_MSG.get(campo, f"Valor inválido para el campo '{campo}'"))
            attr, encrypted = CAMPO_ATTR_MAP.get(campo, (None, False))
            if not attr:
                continue
            if encrypted:
                setattr(estudiante, attr, encrypt_data(str(valor_nuevo)))
            elif campo in ("estrato", "semestre"):
                setattr(estudiante, attr, int(valor_nuevo))
            elif campo == "ingreso_familiar":
                rango_key = None
                for k, r in SMMLV_RANGOS.items():
                    if r["label"] == valor_nuevo:
                        rango_key = k
                        break
                setattr(estudiante, attr, SMMLV_RANGOS[rango_key]["valor_promedio"] if rango_key else int(valor_nuevo))
            else:
                setattr(estudiante, attr, str(valor_nuevo))
