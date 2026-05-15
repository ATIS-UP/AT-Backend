"""Aplicación principal FastAPI"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.error_handlers import register_error_handlers
from app.routers import auth, estudiantes, alertas, admin, dashboard, encuestas, artefactos, parametrizacion, registros_casos, actividades_institucionales, anexos_actividades
from app.database import Base, engine
from app.models.caso_especial import RegistroCasoEspecial, HistorialRegistro


@asynccontextmanager
async def lifespan(app: FastAPI):
    """application lifecycle. create tables if not exist."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de Alertas Tempranas - Universidad de Pamplona",
    lifespan=lifespan
)

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
app.include_router(actividades_institucionales.router)
app.include_router(anexos_actividades.router)


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)