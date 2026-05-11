"""service layer for system parametrization operations"""
import json
from typing import Optional
from sqlalchemy.orm import Session

from app.exceptions import EntityNotFoundError, ValidationError
from app.models.sistema import Parametrizacion
from app.utils.audit import AuditService


class ParametrizacionService:
    """encapsulates business logic for system parameters"""

    # prefixes used to group parameters by category
    PREFIXES = ("UMBRAL_", "PERIODO_", "NOTIFICAR_")

    def __init__(self, db: Session):
        self.db = db

    # -- type validation --

    def _validate_value(self, valor: str, tipo: str) -> None:
        """validate that valor conforms to the declared tipo, raises ValidationError"""
        if tipo == "texto":
            if len(valor) > 500:
                raise ValidationError(
                    "El valor de tipo texto no puede exceder 500 caracteres",
                    fields={"valor": "max 500 caracteres"},
                )
        elif tipo == "numero":
            try:
                float(valor)
            except (ValueError, TypeError):
                raise ValidationError(
                    "El valor debe ser un número válido",
                    fields={"valor": "debe ser parseable como float"},
                )
        elif tipo == "booleano":
            if valor.lower() not in ("true", "false"):
                raise ValidationError(
                    "El valor debe ser 'true' o 'false'",
                    fields={"valor": "debe ser true o false"},
                )
        elif tipo == "json":
            try:
                json.loads(valor)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError(
                    "El valor debe ser JSON válido",
                    fields={"valor": "JSON inválido"},
                )
        else:
            raise ValidationError(
                f"Tipo de parámetro desconocido: {tipo}",
                fields={"tipo": "debe ser texto, numero, booleano o json"},
            )

    # -- helpers --

    def _to_dict(self, param: Parametrizacion) -> dict:
        """convert a parametrizacion orm instance to a plain dict"""
        return {
            "id": str(param.id),
            "clave": param.clave,
            "valor": param.valor,
            "descripcion": param.descripcion,
            "tipo": param.tipo,
            "updated_at": param.updated_at.isoformat() if param.updated_at else None,
            "created_at": param.created_at.isoformat() if param.created_at else None,
        }

    def _get_prefix(self, clave: str) -> str:
        """determine the group prefix for a parameter key"""
        for prefix in self.PREFIXES:
            if clave.startswith(prefix):
                return prefix.rstrip("_")
        return "OTROS"

    # -- public methods --

    def listar(self) -> list[dict]:
        """list all parameters grouped by prefix (UMBRAL_, PERIODO_, NOTIFICAR_)"""
        params = (
            self.db.query(Parametrizacion)
            .order_by(Parametrizacion.clave)
            .all()
        )

        groups: dict[str, list[dict]] = {}
        for param in params:
            group_name = self._get_prefix(param.clave)
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(self._to_dict(param))

        return [
            {"grupo": grupo, "parametros": items}
            for grupo, items in groups.items()
        ]

    def obtener(self, param_id: str) -> dict:
        """get a single parameter by id, raises EntityNotFoundError if missing"""
        param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.id == param_id)
            .first()
        )
        if not param:
            raise EntityNotFoundError("Parametrizacion", param_id)
        return self._to_dict(param)

    def actualizar(
        self, param_id: str, nuevo_valor: str, usuario_id: str, ip: str
    ) -> dict:
        """update a parameter value after type validation, log to audit"""
        param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.id == param_id)
            .first()
        )
        if not param:
            raise EntityNotFoundError("Parametrizacion", param_id)

        # validate the new value against the declared type
        self._validate_value(nuevo_valor, param.tipo)

        valor_anterior = param.valor
        param.valor = nuevo_valor
        self.db.commit()
        self.db.refresh(param)

        AuditService.log_actualizar(
            self.db,
            usuario_id,
            "Parametrizacion",
            str(param.id),
            {"valor": valor_anterior},
            {"valor": nuevo_valor},
            ip,
        )

        return self._to_dict(param)

    def obtener_por_clave(self, clave: str) -> dict:
        """get a parameter by its key name, raises EntityNotFoundError if missing"""
        param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.clave == clave)
            .first()
        )
        if not param:
            raise EntityNotFoundError("Parametrizacion", clave)
        return self._to_dict(param)

    def get_umbrales(self) -> dict:
        """return risk thresholds from parametrizacion table as floats"""
        rojo_param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.clave == "UMBRAL_ROJO")
            .first()
        )
        amarillo_param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.clave == "UMBRAL_AMARILLO")
            .first()
        )

        if not rojo_param:
            raise EntityNotFoundError("Parametrizacion", "UMBRAL_ROJO")
        if not amarillo_param:
            raise EntityNotFoundError("Parametrizacion", "UMBRAL_AMARILLO")

        try:
            rojo = float(rojo_param.valor)
        except (ValueError, TypeError):
            raise ValidationError(
                "UMBRAL_ROJO no contiene un valor numérico válido",
                fields={"UMBRAL_ROJO": rojo_param.valor},
            )

        try:
            amarillo = float(amarillo_param.valor)
        except (ValueError, TypeError):
            raise ValidationError(
                "UMBRAL_AMARILLO no contiene un valor numérico válido",
                fields={"UMBRAL_AMARILLO": amarillo_param.valor},
            )

        return {"rojo": rojo, "amarillo": amarillo}

    def get_periodo_actual(self) -> str:
        """return the value of PERIODO_ACTUAL parameter"""
        param = (
            self.db.query(Parametrizacion)
            .filter(Parametrizacion.clave == "PERIODO_ACTUAL")
            .first()
        )
        if not param:
            raise EntityNotFoundError("Parametrizacion", "PERIODO_ACTUAL")
        return param.valor
