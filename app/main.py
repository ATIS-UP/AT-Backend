"""Aplicación principal FastAPI"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import text

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import get_db
from app.error_handlers import register_error_handlers
from app.routers import auth, estudiantes, alertas, admin, dashboard, encuestas, artefactos, parametrizacion, registros_casos, novedades_casos, actividades_institucionales, anexos_actividades, caracterizacion, bienestar, monitoreo
from app.routers.auth import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """application lifecycle. tables are managed by alembic migrations."""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de Alertas Tempranas - Universidad de Pamplona",
    lifespan=lifespan
)

# SlowAPI rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global error handlers
register_error_handlers(app)

# CORS - origins configured via CORS_ORIGIN env var (comma-separated)
origins = [origin.strip() for origin in settings.CORS_ORIGIN.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# CSP - allow blob: images for auth-protected download URLs
@app.middleware("http")
async def csp_middleware(request, call_next):
    response = await call_next(request)
    existing = response.headers.get('Content-Security-Policy', '')
    if 'blob:' not in existing:
        if existing:
            response.headers['Content-Security-Policy'] = existing + "; img-src 'self' data: blob:"
        else:
            response.headers['Content-Security-Policy'] = "img-src 'self' data: blob:"
    return response

# Routers
app.include_router(auth.router)
app.include_router(estudiantes.router)
app.include_router(alertas.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(encuestas.router)
app.include_router(artefactos.router)
app.include_router(parametrizacion.router)
app.include_router(registros_casos.router)
app.include_router(novedades_casos.router)
app.include_router(actividades_institucionales.router)
app.include_router(anexos_actividades.router)
app.include_router(caracterizacion.router)
app.include_router(bienestar.router)
app.include_router(monitoreo.router)


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    """Health check with database connectivity verification."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)