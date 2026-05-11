"""domain exceptions for the sat application."""


class AppError(Exception):
    """base application error"""

    def __init__(self, message: str, error_code: str, status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class EntityNotFoundError(AppError):
    """raised when a requested entity does not exist"""

    def __init__(self, entity: str, entity_id: str):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(
            message=f"{entity} no encontrado",
            error_code="ENTITY_NOT_FOUND",
            status_code=404,
        )


class ValidationError(AppError):
    """raised when input data fails domain validation"""

    def __init__(self, message: str, fields: dict = None):
        self.fields = fields or {}
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
        )


class PermissionDeniedError(AppError):
    """raised when user lacks a required permission"""

    def __init__(self, permiso_codigo: str):
        self.permiso_codigo = permiso_codigo
        super().__init__(
            message=f"Permiso requerido: {permiso_codigo}",
            error_code="PERMISSION_DENIED",
            status_code=403,
        )


class DuplicateEntityError(AppError):
    """raised when attempting to create an entity that already exists"""

    def __init__(self, entity: str, field: str, value: str):
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(
            message=f"{entity} con {field}={value} ya existe",
            error_code="DUPLICATE_ENTITY",
            status_code=409,
        )


class AuthenticationError(AppError):
    """raised when authentication fails (invalid or expired token)"""

    def __init__(self, message: str = "Token inválido o expirado"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
        )
