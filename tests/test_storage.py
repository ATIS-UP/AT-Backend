"""Tests de app.utils.storage: backend local (tmp_path) y s3 (cliente boto3 mockeado)."""
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet

from app.config import settings
from app.utils import storage


KEY = "uploads/evidencias_casos/reg-1/foto.png"
PNG = b"\x89PNG\r\n\x1a\n" + b"contenido de la foto"


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
    def test_guardar_cifra_y_leer_descifra(self, local):
        storage.guardar(KEY, PNG, "image/png")

        en_disco = (local / KEY).read_bytes()
        assert en_disco.startswith(storage.PREFIJO_CIFRADO)
        assert b"contenido de la foto" not in en_disco
        assert storage.leer(KEY) == PNG

    def test_lee_archivo_viejo_sin_cifrar(self, local):
        (local / KEY).parent.mkdir(parents=True)
        (local / KEY).write_bytes(PNG)

        assert storage.leer(KEY) == PNG

    def test_clave_distinta_da_error(self, local, monkeypatch):
        storage.guardar(KEY, PNG, "image/png")
        monkeypatch.setattr(storage, "fernet", Fernet(Fernet.generate_key()))

        with pytest.raises(RuntimeError):
            storage.leer(KEY)

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
    def test_guardar_sube_cifrado(self, s3):
        storage.guardar(KEY, PNG, "image/png")

        kwargs = s3.put_object.call_args.kwargs
        assert kwargs["Bucket"] == "bucket-test"
        assert kwargs["Key"] == KEY
        assert kwargs["ContentType"] == "image/png"
        assert kwargs["Body"].startswith(storage.PREFIJO_CIFRADO)
        assert b"contenido de la foto" not in kwargs["Body"]

    def test_leer_descifra(self, s3):
        cifrado = storage._cifrar(PNG)
        s3.get_object.return_value = {"Body": MagicMock(read=lambda: cifrado)}

        assert storage.leer(KEY) == PNG
        s3.get_object.assert_called_once_with(Bucket="bucket-test", Key=KEY)

    def test_leer_archivo_viejo_sin_cifrar(self, s3):
        s3.get_object.return_value = {"Body": MagicMock(read=lambda: PNG)}

        assert storage.leer(KEY) == PNG

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
