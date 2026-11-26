"""Tests del router de evidencias de casos: auditoría al subir y al borrar fotos."""
import io
import uuid
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import UploadFile

from app.routers import evidencias_casos as router

PNG = b"\x89PNG\r\n\x1a\n" + b"contenido de la foto"


def _request(ip="10.0.0.5"):
    request = MagicMock()
    request.client.host = ip
    return request


@pytest.fixture
def storage():
    with patch.object(router, "storage") as mock:
        yield mock


@pytest.fixture
def audit():
    with patch.object(router, "AuditService") as mock:
        yield mock


class TestSubirEvidencia:
    def _db(self):
        db = MagicMock()
        db.get.return_value = MagicMock()  # el registro existe
        db.query.return_value.filter.return_value.count.return_value = 0
        return db

    def test_audita_antes_del_commit_y_sin_nombre_original(self, storage, audit):
        db = self._db()
        usuario = MagicMock(id=uuid.uuid4())
        registro_id = str(uuid.uuid4())
        archivo = UploadFile(file=io.BytesIO(PNG), filename="foto_de_alguien.png")
        orden = MagicMock()
        orden.attach_mock(audit.log_crear, "log_crear")
        orden.attach_mock(db.commit, "commit")

        resp = router.subir_evidencia(registro_id, _request(), archivo, db, usuario)

        kwargs = audit.log_crear.call_args.kwargs
        assert kwargs["entidad"] == "EvidenciaCaso"
        assert kwargs["entidad_id"] == resp["id"]
        assert kwargs["usuario_id"] == str(usuario.id)
        assert kwargs["ip"] == "10.0.0.5"
        assert kwargs["datos"] == {"registro_id": registro_id, "tipo": "image/png", "bytes": len(PNG)}
        assert "foto_de_alguien" not in str(kwargs)
        assert [c[0] for c in orden.mock_calls] == ["log_crear", "commit"]

    def test_no_audita_si_la_imagen_es_invalida(self, storage, audit):
        archivo = UploadFile(file=io.BytesIO(b"no es png"), filename="x.png")

        with pytest.raises(Exception):
            router.subir_evidencia(str(uuid.uuid4()), _request(), archivo, self._db(), MagicMock())

        audit.log_crear.assert_not_called()
        storage.guardar.assert_not_called()


class TestEliminarEvidencia:
    def test_audita_borra_y_luego_elimina_archivo(self, storage, audit):
        evidencia = MagicMock(id=uuid.uuid4(), registro_id=uuid.uuid4(), ruta="reg/a.png", tipo="image/png")
        db = MagicMock()
        db.get.return_value = evidencia
        usuario = MagicMock(id=uuid.uuid4())
        orden = MagicMock()
        orden.attach_mock(audit.log_eliminar, "log_eliminar")
        orden.attach_mock(db.commit, "commit")
        orden.attach_mock(storage.eliminar, "eliminar")

        router.eliminar_evidencia(str(evidencia.id), _request(), db, usuario)

        assert orden.mock_calls == [
            call.log_eliminar(
                db=db,
                usuario_id=str(usuario.id),
                entidad="EvidenciaCaso",
                entidad_id=str(evidencia.id),
                datos_eliminados={"registro_id": str(evidencia.registro_id), "tipo": "image/png"},
                ip="10.0.0.5",
            ),
            call.commit(),
            call.eliminar("uploads/evidencias_casos/reg/a.png"),
        ]
        db.delete.assert_called_once_with(evidencia)
