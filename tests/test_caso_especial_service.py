"""tests for caso especial service (Phase 1: descripcion, bloqueo CERRADO, novedades)."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import EntityNotFoundError, ValidationError
from app.models.caso_especial import (
    TipoRegistroCaso, EstadoRegistroCaso, AccionHistorial
)
from app.models.estudiante import EstadoEstudiante
from app.services.caso_especial_service import CasoEspecialService


def _make_estudiante(estado=EstadoEstudiante.ACTIVO):
    """helper to create a mock estudiante with encrypted-like fields."""
    est = MagicMock()
    est.id = uuid.uuid4()
    est.codigo = "U001"
    est.documento = "enc"
    est.nombres = "enc"
    est.apellidos = "enc"
    est.programa = "Trabajo Social"
    est.semestre = 5
    est.estado = estado
    return est


def _make_novedad(tipo_caso=TipoRegistroCaso.RENDIMIENTO_ACADEMICO, descripcion=None):
    """helper to create a mock novedad."""
    nov = MagicMock()
    nov.id = uuid.uuid4()
    nov.nombre = "Bajo rendimiento"
    nov.descripcion = descripcion
    nov.tipo_caso = tipo_caso
    return nov


def _make_registro(
    estado=EstadoRegistroCaso.ACTIVO,
    tipo=TipoRegistroCaso.RENDIMIENTO_ACADEMICO,
    estudiante=None,
    novedad=None,
    observaciones="Observaciones iniciales",
):
    """helper to create a mock registro de caso especial."""
    reg = MagicMock()
    reg.id = uuid.uuid4()
    reg.estudiante_id = estudiante.id if estudiante else uuid.uuid4()
    reg.estudiante = estudiante
    reg.tipo = tipo
    reg.estado = estado
    reg.observaciones = observaciones
    reg.novedad_id = novedad.id if novedad else uuid.uuid4()
    reg.novedad = novedad
    reg.responsable_id = uuid.uuid4()
    reg.responsable_nombre = "Test User"
    reg.created_at = datetime(2025, 1, 1, 12, 0, 0)
    reg.updated_at = datetime(2025, 1, 1, 12, 0, 0)
    return reg


class TestCasoEspecialServiceDescripcionNovedad:
    """validates that novedad.descripcion is propagated in the response."""

    def test_registro_response_incluye_descripcion_novedad(self):
        estudiante = _make_estudiante()
        novedad = _make_novedad(descripcion="Descripcion oficial de la novedad")
        registro = _make_registro(estudiante=estudiante, novedad=novedad)

        db = MagicMock()
        service = CasoEspecialService(db)
        response = service._registro_to_response(registro)

        assert response.novedad is not None
        assert response.novedad.id == str(novedad.id)
        assert response.novedad.nombre == novedad.nombre
        assert response.novedad.descripcion == "Descripcion oficial de la novedad"

    def test_registro_response_novedad_sin_descripcion(self):
        estudiante = _make_estudiante()
        novedad = _make_novedad(descripcion=None)
        registro = _make_registro(estudiante=estudiante, novedad=novedad)

        db = MagicMock()
        service = CasoEspecialService(db)
        response = service._registro_to_response(registro)

        assert response.novedad is not None
        assert response.novedad.descripcion is None

    def test_registro_response_sin_novedad(self):
        estudiante = _make_estudiante()
        registro = _make_registro(estudiante=estudiante, novedad=None)

        db = MagicMock()
        service = CasoEspecialService(db)
        response = service._registro_to_response(registro)

        assert response.novedad is None


class TestCasoEspecialServiceCrearBloqueoCerrado:
    """validates that crear() blocks when student has a CERRADO record."""

    def test_crear_bloquea_si_estudiante_tiene_caso_cerrado(self):
        estudiante = _make_estudiante()
        novedad = _make_novedad()
        registro_cerrado = _make_registro(estado=EstadoRegistroCaso.CERRADO)

        db = MagicMock()
        # first .query(Estudiante) call returns estudiante
        # second .query(RegistroCasoEspecial) call returns registro_cerrado
        db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=estudiante)))),
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=registro_cerrado)))),
        ]

        service = CasoEspecialService(db)

        from app.schemas.caso_especial import RegistroCasoCreate
        data = RegistroCasoCreate(
            estudiante_id=str(estudiante.id),
            tipo=TipoRegistroCaso.RENDIMIENTO_ACADEMICO.value,
            novedad_id=str(novedad.id),
            observaciones="Test",
        )

        with pytest.raises(ValidationError) as exc:
            service.crear(data, str(uuid.uuid4()), "User")
        assert "cerrado" in str(exc.value.message).lower()

    def test_crear_bloquea_si_estudiante_no_activo(self):
        estudiante = _make_estudiante(estado=EstadoEstudiante.INACTIVO)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = estudiante

        service = CasoEspecialService(db)

        from app.schemas.caso_especial import RegistroCasoCreate
        data = RegistroCasoCreate(
            estudiante_id=str(estudiante.id),
            tipo=TipoRegistroCaso.RENDIMIENTO_ACADEMICO.value,
            novedad_id=str(uuid.uuid4()),
            observaciones="Test",
        )

        with pytest.raises(ValidationError) as exc:
            service.crear(data, str(uuid.uuid4()), "User")
        assert "estado" in str(exc.value.message).lower()

    def test_crear_bloquea_sin_novedad(self):
        estudiante = _make_estudiante()

        db = MagicMock()
        # query(Estudiante) -> estudiante
        # query(RegistroCasoEspecial) -> None (no cerrado)
        db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=estudiante)))),
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))),
        ]

        service = CasoEspecialService(db)

        from app.schemas.caso_especial import RegistroCasoCreate
        data = RegistroCasoCreate(
            estudiante_id=str(estudiante.id),
            tipo=TipoRegistroCaso.RENDIMIENTO_ACADEMICO.value,
            novedad_id="",  # empty
            observaciones="Test",
        )

        with pytest.raises(ValidationError) as exc:
            service.crear(data, str(uuid.uuid4()), "User")
        assert "novedad" in str(exc.value.message).lower()

    def test_crear_bloquea_si_novedad_no_corresponde_al_tipo(self):
        estudiante = _make_estudiante()
        novedad = _make_novedad(tipo_caso=TipoRegistroCaso.PSICOSOCIAL)

        db = MagicMock()
        db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=estudiante)))),
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))),
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=novedad)))),
        ]

        service = CasoEspecialService(db)

        from app.schemas.caso_especial import RegistroCasoCreate
        data = RegistroCasoCreate(
            estudiante_id=str(estudiante.id),
            tipo=TipoRegistroCaso.RENDIMIENTO_ACADEMICO.value,
            novedad_id=str(novedad.id),
            observaciones="Test",
        )

        with pytest.raises(ValidationError) as exc:
            service.crear(data, str(uuid.uuid4()), "User")
        assert "novedad" in str(exc.value.message).lower()

    def test_crear_exitoso_crea_registro_y_historial(self):
        estudiante = _make_estudiante()
        novedad = _make_novedad()

        db = MagicMock()
        db.query.side_effect = [
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=estudiante)))),
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))),
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=novedad)))),
        ]

        created_registros = []

        original_init = None

        def fake_add(obj):
            # Captura el registro creado (el primer add es el registro, el segundo el historial)
            if not created_registros:
                # Asignamos el estudiante al registro para que _registro_to_response funcione
                obj.estudiante = estudiante
                obj.novedad = novedad
                obj.created_at = datetime(2025, 1, 1, 12, 0, 0)
                obj.updated_at = datetime(2025, 1, 1, 12, 0, 0)
                created_registros.append(obj)
            else:
                created_registros.append(obj)

        db.add.side_effect = fake_add
        db.refresh = MagicMock(side_effect=lambda obj: None)

        service = CasoEspecialService(db)

        from app.schemas.caso_especial import RegistroCasoCreate
        data = RegistroCasoCreate(
            estudiante_id=str(estudiante.id),
            tipo=TipoRegistroCaso.RENDIMIENTO_ACADEMICO.value,
            novedad_id=str(novedad.id),
            observaciones="Caso nuevo",
        )

        service.crear(data, str(uuid.uuid4()), "User")

        # Se agregaron 2 entidades: el registro y el historial de apertura
        assert db.add.call_count == 2
        db.commit.assert_called_once()
        db.flush.assert_called_once()


class TestCasoEspecialServiceAgregarHistorialBloqueoCerrado:
    """validates that agregar_historial() blocks when registro is CERRADO."""

    def test_agregar_historial_bloquea_si_cerrado(self):
        registro = _make_registro(estado=EstadoRegistroCaso.CERRADO)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = registro

        service = CasoEspecialService(db)

        with pytest.raises(ValidationError) as exc:
            service.agregar_historial(
                str(registro.id),
                AccionHistorial.SEGUIMIENTO.value,
                "Intentar agregar seguimiento",
                str(uuid.uuid4()),
                "User",
            )
        assert "cerrado" in str(exc.value.message).lower()
        db.add.assert_not_called()

    def test_agregar_historial_exitoso_si_activo(self):
        estudiante = _make_estudiante()
        novedad = _make_novedad()
        registro = _make_registro(
            estado=EstadoRegistroCaso.ACTIVO,
            estudiante=estudiante,
            novedad=novedad,
        )

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = registro

        service = CasoEspecialService(db)

        service.agregar_historial(
            str(registro.id),
            AccionHistorial.SEGUIMIENTO.value,
            "Seguimiento OK",
            str(uuid.uuid4()),
            "User",
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_agregar_historial_retorna_none_si_no_existe(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        service = CasoEspecialService(db)

        result = service.agregar_historial(
            str(uuid.uuid4()),
            AccionHistorial.SEGUIMIENTO.value,
            "Test",
            str(uuid.uuid4()),
            "User",
        )

        assert result is None


class TestCasoEspecialServiceActualizarEstado:
    """validates state transitions."""

    def test_actualizar_bloquea_estado_igual(self):
        registro = _make_registro(estado=EstadoRegistroCaso.ACTIVO)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = registro

        service = CasoEspecialService(db)

        from app.schemas.caso_especial import RegistroCasoUpdate
        data = RegistroCasoUpdate(estado=EstadoRegistroCaso.ACTIVO.value)

        with pytest.raises(ValidationError) as exc:
            service.actualizar(str(registro.id), data, str(uuid.uuid4()), "User")
        assert "ya se encuentra" in str(exc.value.message).lower()

    def test_actualizar_a_cerrado_registra_historial_cierre(self):
        estudiante = _make_estudiante()
        novedad = _make_novedad()
        registro = _make_registro(
            estado=EstadoRegistroCaso.ACTIVO,
            estudiante=estudiante,
            novedad=novedad,
        )

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = registro
        db.refresh = MagicMock(side_effect=lambda obj: None)

        service = CasoEspecialService(db)

        from app.schemas.caso_especial import RegistroCasoUpdate
        data = RegistroCasoUpdate(
            estado=EstadoRegistroCaso.CERRADO.value,
            observaciones="Cerrado por seguimiento exitoso",
        )

        service.actualizar(str(registro.id), data, str(uuid.uuid4()), "User")
        # Se registra historial de cierre
        assert db.add.call_count >= 1
        db.commit.assert_called_once()
