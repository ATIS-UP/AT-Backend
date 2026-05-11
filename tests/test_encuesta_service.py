"""tests for encuesta service."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError
from app.services.encuesta_service import EncuestaService


def _make_encuesta(
    estado="BORRADOR",
    preguntas=None,
    titulo="Encuesta Test",
    descripcion="Desc",
    periodo="2025-1",
):
    """helper to create a mock encuesta object."""
    encuesta = MagicMock()
    encuesta.id = uuid.uuid4()
    encuesta.titulo = titulo
    encuesta.descripcion = descripcion
    encuesta.preguntas = preguntas or []
    encuesta.estado = estado
    encuesta.periodo = periodo
    encuesta.fecha_inicio = None
    encuesta.fecha_fin = None
    encuesta.es_publica = False
    encuesta.created_at = datetime(2025, 1, 1, 12, 0, 0)
    encuesta.updated_at = datetime(2025, 1, 1, 12, 0, 0)
    return encuesta


def _make_respuesta(encuesta_id, estudiante_id, respuestas):
    """helper to create a mock respuesta object."""
    resp = MagicMock()
    resp.id = uuid.uuid4()
    resp.encuesta_id = encuesta_id
    resp.estudiante_id = estudiante_id
    resp.respuestas = respuestas
    resp.created_at = datetime(2025, 1, 2, 10, 0, 0)
    return resp


class TestEncuestaServiceCrear:
    """tests for creating surveys."""

    @patch("app.services.encuesta_service.AuditService")
    def test_crear_encuesta_basica(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        data = {
            "titulo": "Mi Encuesta",
            "descripcion": "Una descripcion",
            "preguntas": [
                {"id": 1, "texto": "Pregunta 1", "tipo": "texto_libre"}
            ],
            "periodo": "2025-1",
        }

        # mock db.refresh to set attributes on the added object
        def refresh_side_effect(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2025, 1, 1)
            obj.updated_at = datetime(2025, 1, 1)

        db.refresh.side_effect = refresh_side_effect

        result = service.crear(data, usuario_id="user-123")

        assert result["titulo"] == "Mi Encuesta"
        assert result["estado"] == "BORRADOR"
        assert db.add.called
        assert db.commit.called

    @patch("app.services.encuesta_service.AuditService")
    def test_crear_encuesta_sin_preguntas(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        data = {"titulo": "Sin preguntas", "preguntas": []}

        def refresh_side_effect(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2025, 1, 1)
            obj.updated_at = datetime(2025, 1, 1)

        db.refresh.side_effect = refresh_side_effect

        # creating with empty questions is allowed (publishing is not)
        result = service.crear(data, usuario_id="user-123")
        assert result["titulo"] == "Sin preguntas"

    @patch("app.services.encuesta_service.AuditService")
    def test_crear_encuesta_tipo_invalido_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        data = {
            "titulo": "Mala",
            "preguntas": [{"id": 1, "texto": "Q", "tipo": "invalido"}],
        }

        with pytest.raises(ValidationError, match="Tipo de pregunta invalido"):
            service.crear(data, usuario_id="user-123")

    @patch("app.services.encuesta_service.AuditService")
    def test_crear_opcion_multiple_sin_opciones_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        data = {
            "titulo": "Mala",
            "preguntas": [
                {"id": 1, "texto": "Q", "tipo": "opcion_multiple", "opciones": []}
            ],
        }

        with pytest.raises(ValidationError, match="al menos 2 opciones"):
            service.crear(data, usuario_id="user-123")


class TestEncuestaServicePublicar:
    """tests for publishing surveys."""

    @patch("app.services.encuesta_service.AuditService")
    def test_publicar_encuesta_con_preguntas(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(
            estado="BORRADOR",
            preguntas=[{"id": 1, "texto": "Q1", "tipo": "texto_libre"}],
        )
        db.query.return_value.filter.return_value.first.return_value = encuesta

        result = service.publicar(str(encuesta.id), "user-123")

        assert encuesta.estado == "PUBLICADA"
        assert db.commit.called

    @patch("app.services.encuesta_service.AuditService")
    def test_publicar_sin_preguntas_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="BORRADOR", preguntas=[])
        db.query.return_value.filter.return_value.first.return_value = encuesta

        with pytest.raises(ValidationError, match="al menos una pregunta"):
            service.publicar(str(encuesta.id), "user-123")

    @patch("app.services.encuesta_service.AuditService")
    def test_publicar_encuesta_no_borrador_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="PUBLICADA")
        db.query.return_value.filter.return_value.first.return_value = encuesta

        with pytest.raises(ValidationError, match="estado BORRADOR"):
            service.publicar(str(encuesta.id), "user-123")


class TestEncuestaServiceCerrar:
    """tests for closing surveys."""

    @patch("app.services.encuesta_service.AuditService")
    def test_cerrar_encuesta_publicada(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="PUBLICADA")
        db.query.return_value.filter.return_value.first.return_value = encuesta

        service.cerrar(str(encuesta.id), "user-123")

        assert encuesta.estado == "CERRADA"
        assert db.commit.called

    @patch("app.services.encuesta_service.AuditService")
    def test_cerrar_encuesta_borrador_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="BORRADOR")
        db.query.return_value.filter.return_value.first.return_value = encuesta

        with pytest.raises(ValidationError, match="estado PUBLICADA"):
            service.cerrar(str(encuesta.id), "user-123")


class TestEncuestaServiceRegistrarRespuesta:
    """tests for registering student responses."""

    @patch("app.services.encuesta_service.AuditService")
    def test_registrar_respuesta_exitosa(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="PUBLICADA")
        estudiante_id = str(uuid.uuid4())

        # first query returns encuesta, second returns no existing response
        query_mock = MagicMock()
        filter_mock = MagicMock()

        def query_side_effect(model):
            mock = MagicMock()
            if model.__tablename__ == "encuestas":
                mock.filter.return_value.first.return_value = encuesta
            else:
                mock.filter.return_value.first.return_value = None
            return mock

        db.query.side_effect = query_side_effect

        def refresh_side_effect(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2025, 1, 2)

        db.refresh.side_effect = refresh_side_effect

        respuestas = [{"pregunta_id": 1, "valor": "Mi respuesta"}]
        result = service.registrar_respuesta(str(encuesta.id), estudiante_id, respuestas)

        assert result["estudiante_id"] == estudiante_id
        assert db.add.called
        assert db.commit.called

    @patch("app.services.encuesta_service.AuditService")
    def test_registrar_respuesta_encuesta_no_publicada_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="BORRADOR")
        db.query.return_value.filter.return_value.first.return_value = encuesta

        with pytest.raises(ValidationError, match="estado PUBLICADA"):
            service.registrar_respuesta(str(encuesta.id), "est-1", [])

    @patch("app.services.encuesta_service.AuditService")
    def test_registrar_respuesta_duplicada_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="PUBLICADA")
        existing_resp = MagicMock()

        def query_side_effect(model):
            mock = MagicMock()
            if model.__tablename__ == "encuestas":
                mock.filter.return_value.first.return_value = encuesta
            else:
                mock.filter.return_value.first.return_value = existing_resp
            return mock

        db.query.side_effect = query_side_effect

        with pytest.raises(DuplicateEntityError):
            service.registrar_respuesta(str(encuesta.id), "est-1", [])


class TestEncuestaServiceObtenerResultados:
    """tests for aggregating survey results."""

    @patch("app.services.encuesta_service.AuditService")
    def test_resultados_opcion_multiple(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta_id = uuid.uuid4()
        encuesta = _make_encuesta(
            estado="CERRADA",
            preguntas=[
                {
                    "id": 1,
                    "texto": "Color favorito?",
                    "tipo": "opcion_multiple",
                    "opciones": ["rojo", "azul", "verde"],
                }
            ],
        )
        encuesta.id = encuesta_id

        respuestas = [
            _make_respuesta(encuesta_id, "e1", [{"pregunta_id": 1, "valor": "rojo"}]),
            _make_respuesta(encuesta_id, "e2", [{"pregunta_id": 1, "valor": "azul"}]),
            _make_respuesta(encuesta_id, "e3", [{"pregunta_id": 1, "valor": "rojo"}]),
        ]

        def query_side_effect(model):
            mock = MagicMock()
            if model.__tablename__ == "encuestas":
                mock.filter.return_value.first.return_value = encuesta
            else:
                mock.filter.return_value.all.return_value = respuestas
            return mock

        db.query.side_effect = query_side_effect

        result = service.obtener_resultados(str(encuesta_id))

        assert result["total_respuestas"] == 3
        pregunta_result = result["resultados_por_pregunta"][0]
        assert pregunta_result["tipo"] == "opcion_multiple"
        assert pregunta_result["distribucion"]["rojo"] == 2
        assert pregunta_result["distribucion"]["azul"] == 1

    @patch("app.services.encuesta_service.AuditService")
    def test_resultados_escala_likert(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta_id = uuid.uuid4()
        encuesta = _make_encuesta(
            estado="CERRADA",
            preguntas=[
                {"id": 1, "texto": "Satisfaccion?", "tipo": "escala_likert"}
            ],
        )
        encuesta.id = encuesta_id

        respuestas = [
            _make_respuesta(encuesta_id, "e1", [{"pregunta_id": 1, "valor": 4}]),
            _make_respuesta(encuesta_id, "e2", [{"pregunta_id": 1, "valor": 5}]),
            _make_respuesta(encuesta_id, "e3", [{"pregunta_id": 1, "valor": 3}]),
        ]

        def query_side_effect(model):
            mock = MagicMock()
            if model.__tablename__ == "encuestas":
                mock.filter.return_value.first.return_value = encuesta
            else:
                mock.filter.return_value.all.return_value = respuestas
            return mock

        db.query.side_effect = query_side_effect

        result = service.obtener_resultados(str(encuesta_id))

        pregunta_result = result["resultados_por_pregunta"][0]
        assert pregunta_result["tipo"] == "escala_likert"
        assert pregunta_result["promedio"] == 4.0
        assert pregunta_result["distribucion"]["3"] == 1
        assert pregunta_result["distribucion"]["4"] == 1
        assert pregunta_result["distribucion"]["5"] == 1

    @patch("app.services.encuesta_service.AuditService")
    def test_resultados_texto_libre(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta_id = uuid.uuid4()
        encuesta = _make_encuesta(
            estado="CERRADA",
            preguntas=[
                {"id": 1, "texto": "Comentarios?", "tipo": "texto_libre"}
            ],
        )
        encuesta.id = encuesta_id

        respuestas = [
            _make_respuesta(encuesta_id, "e1", [{"pregunta_id": 1, "valor": "Bien"}]),
            _make_respuesta(encuesta_id, "e2", [{"pregunta_id": 1, "valor": "Mal"}]),
        ]

        def query_side_effect(model):
            mock = MagicMock()
            if model.__tablename__ == "encuestas":
                mock.filter.return_value.first.return_value = encuesta
            else:
                mock.filter.return_value.all.return_value = respuestas
            return mock

        db.query.side_effect = query_side_effect

        result = service.obtener_resultados(str(encuesta_id))

        pregunta_result = result["resultados_por_pregunta"][0]
        assert pregunta_result["tipo"] == "texto_libre"
        assert pregunta_result["respuestas_texto"] == ["Bien", "Mal"]


class TestEncuestaServiceObtener:
    """tests for getting a single survey."""

    def test_obtener_encuesta_no_existente_raises(self):
        db = MagicMock()
        service = EncuestaService(db)

        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(EntityNotFoundError):
            service.obtener("nonexistent-id")


class TestEncuestaServiceActualizar:
    """tests for updating surveys."""

    @patch("app.services.encuesta_service.AuditService")
    def test_actualizar_encuesta_publicada_raises(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta(estado="PUBLICADA")
        db.query.return_value.filter.return_value.first.return_value = encuesta

        with pytest.raises(ValidationError, match="estado BORRADOR"):
            service.actualizar(str(encuesta.id), {"titulo": "Nuevo"}, "user-1")


class TestEncuestaServiceEliminar:
    """tests for deleting surveys."""

    @patch("app.services.encuesta_service.AuditService")
    def test_eliminar_encuesta(self, mock_audit):
        db = MagicMock()
        service = EncuestaService(db)

        encuesta = _make_encuesta()
        db.query.return_value.filter.return_value.first.return_value = encuesta

        service.eliminar(str(encuesta.id), "user-1")

        assert db.delete.called
        assert db.commit.called
