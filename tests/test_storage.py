"""Tests de app.utils.storage: backend local (tmp_path) y s3 (cliente boto3 mockeado)."""
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.config import settings
from app.utils import storage


KEY = "uploads/evidencias_casos/reg-1/foto.png"


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "UPLOAD_BASE_PATH", str(tmp_path))
    return tmp_path


@pytest.fixture
def s3(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "MINIO_BUCKET", "bucket-test")
    cliente = MagicMock()
    with patch("app.utils.storage._s3_client", return_value=cliente):
        yield cliente


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code}}, "GetObject")


class TestLocal:
    def test_guardar_y_leer(self, local):
        storage.guardar(KEY, b"datos", "image/png")

        assert (local / KEY).read_bytes() == b"datos"
        assert storage.leer(KEY) == b"datos"

    def test_leer_inexistente_devuelve_none(self, local):
        assert storage.leer(KEY) is None

    def test_eliminar(self, local):
        storage.guardar(KEY, b"datos", "image/png")
        storage.eliminar(KEY)

        assert not (local / KEY).exists()
        storage.eliminar(KEY)  # idempotente

    def test_rechaza_clave_fuera_de_la_base(self, local):
        with pytest.raises(ValueError):
            storage.leer("../fuera.txt")


class TestS3:
    def test_guardar_usa_put_object(self, s3):
        storage.guardar(KEY, b"datos", "image/png")

        s3.put_object.assert_called_once_with(
            Bucket="bucket-test", Key=KEY, Body=b"datos", ContentType="image/png",
        )

    def test_leer(self, s3):
        s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"datos")}

        assert storage.leer(KEY) == b"datos"
        s3.get_object.assert_called_once_with(Bucket="bucket-test", Key=KEY)

    def test_leer_inexistente_devuelve_none(self, s3):
        s3.get_object.side_effect = _client_error("NoSuchKey")

        assert storage.leer(KEY) is None

    def test_leer_propaga_otros_errores(self, s3):
        s3.get_object.side_effect = _client_error("AccessDenied")

        with pytest.raises(ClientError):
            storage.leer(KEY)

    def test_eliminar_ignora_errores(self, s3):
        s3.delete_object.side_effect = _client_error("NoSuchKey")

        storage.eliminar(KEY)

        s3.delete_object.assert_called_once_with(Bucket="bucket-test", Key=KEY)


class TestClienteS3:
    def test_usa_timeouts_cortos(self):
        with patch("app.utils.storage.boto3.client") as cliente:
            storage._s3_client()

        config = cliente.call_args.kwargs["config"]
        assert config.connect_timeout == 5
        assert config.read_timeout == 30
        assert config.retries["max_attempts"] == 2


class TestRespuestaArchivo:
    def test_nombre_ascii(self):
        resp = storage.respuesta_archivo(b"x", "foto.png", "image/png")

        assert resp.headers["content-disposition"] == 'attachment; filename="foto.png"'
        assert resp.media_type == "image/png"

    def test_nombre_no_ascii(self):
        resp = storage.respuesta_archivo(b"x", "acción.png", "image/png", headers={"Cache-Control": "no-store"})

        assert resp.headers["content-disposition"] == "attachment; filename*=utf-8''acci%C3%B3n.png"
        assert resp.headers["cache-control"] == "no-store"
