"""tests for global error handlers."""

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.error_handlers import register_error_handlers
from app.exceptions import (
    AppError,
    AuthenticationError,
    DuplicateEntityError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)


def _create_test_app() -> FastAPI:
    """create a minimal fastapi app with error handlers registered."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/raise-not-found")
    async def raise_not_found():
        raise EntityNotFoundError(entity="Estudiante", entity_id="123")

    @app.get("/raise-permission-denied")
    async def raise_permission_denied():
        raise PermissionDeniedError(permiso_codigo="ADMIN_PANEL")

    @app.get("/raise-duplicate")
    async def raise_duplicate():
        raise DuplicateEntityError(entity="User", field="email", value="x@test.com")

    @app.get("/raise-auth-error")
    async def raise_auth_error():
        raise AuthenticationError()

    @app.get("/raise-validation-error")
    async def raise_validation_error():
        raise ValidationError(
            message="Datos inválidos", fields={"email": ["formato inválido"]}
        )

    @app.get("/raise-generic-error")
    async def raise_generic_error():
        raise RuntimeError("something unexpected happened")

    class ItemCreate(BaseModel):
        name: str = Field(..., min_length=1)
        age: int = Field(..., gt=0)

    @app.post("/validate-body")
    async def validate_body(item: ItemCreate):
        return {"ok": True}

    return app


@pytest.fixture
def client():
    app = _create_test_app()
    return TestClient(app, raise_server_exceptions=False)


class TestAppErrorHandler:
    """tests for AppError subclass handling."""

    def test_entity_not_found_returns_404(self, client):
        resp = client.get("/raise-not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Estudiante no encontrado"
        assert body["error_code"] == "ENTITY_NOT_FOUND"
        assert body["status_code"] == 404
        assert body["details"] is None
        assert "timestamp" in body

    def test_permission_denied_returns_403(self, client):
        resp = client.get("/raise-permission-denied")
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_code"] == "PERMISSION_DENIED"
        assert body["status_code"] == 403
        assert "ADMIN_PANEL" in body["message"]

    def test_duplicate_entity_returns_409(self, client):
        resp = client.get("/raise-duplicate")
        assert resp.status_code == 409
        body = resp.json()
        assert body["error_code"] == "DUPLICATE_ENTITY"
        assert body["status_code"] == 409

    def test_authentication_error_returns_401(self, client):
        resp = client.get("/raise-auth-error")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error_code"] == "AUTHENTICATION_ERROR"
        assert body["status_code"] == 401

    def test_domain_validation_error_includes_fields(self, client):
        resp = client.get("/raise-validation-error")
        assert resp.status_code == 422
        body = resp.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["details"] == {"email": ["formato inválido"]}


class TestValidationErrorHandler:
    """tests for pydantic RequestValidationError handling."""

    def test_invalid_body_returns_422_with_field_details(self, client):
        resp = client.post("/validate-body", json={"name": "", "age": -1})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["status_code"] == 422
        assert body["details"] is not None
        assert "timestamp" in body

    def test_missing_fields_returns_422(self, client):
        resp = client.post("/validate-body", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert "details" in body


class TestGenericErrorHandler:
    """tests for unhandled exception handling."""

    def test_generic_error_returns_500_without_internals(self, client):
        resp = client.get("/raise-generic-error")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error_code"] == "INTERNAL_ERROR"
        assert body["status_code"] == 500
        assert body["details"] is None
        assert "timestamp" in body
        # must not expose internal error message
        assert "something unexpected" not in body["message"]
        assert body["message"] == "Error interno del servidor"


class TestResponseFormat:
    """tests that all error responses follow the standardized format."""

    def test_all_responses_have_required_fields(self, client):
        endpoints = [
            "/raise-not-found",
            "/raise-permission-denied",
            "/raise-duplicate",
            "/raise-auth-error",
            "/raise-generic-error",
        ]
        required_keys = {"message", "error_code", "status_code", "details", "timestamp"}
        for endpoint in endpoints:
            resp = client.get(endpoint)
            body = resp.json()
            assert required_keys.issubset(body.keys()), (
                f"{endpoint} missing keys: {required_keys - body.keys()}"
            )
