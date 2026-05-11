"""router for dashboard and statistics"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import require_permiso
from app.models.user import User
from app.models.estudiante import Estudiante, EstadoEstudiante
from app.models.alerta import Alerta, NivelRiesgo, EstadoSeguimiento

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/resumen")
async def get_resumen(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_dashboard"))
):
    """get general dashboard summary"""
    total_estudiantes = db.query(Estudiante).count()
    activos = db.query(Estudiante).filter(Estudiante.estado == EstadoEstudiante.ACTIVO).count()

    total_alertas = db.query(Alerta).count()
    criticas = db.query(Alerta).filter(Alerta.nivel_riesgo == NivelRiesgo.ROJO).count()
    pendientes = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.PENDIENTE).count()
    en_proceso = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.EN_PROCESO).count()
    resueltas = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.RESUELTO).count()

    programas = db.query(
        Estudiante.programa,
        func.count(Estudiante.id).label("total")
    ).group_by(Estudiante.programa).all()

    programas_dist = [{"programa": p.programa, "total": p.total} for p in programas]

    alertas_por_periodo = db.query(
        Alerta.periodo,
        func.count(Alerta.id).label("total")
    ).group_by(Alerta.periodo).order_by(Alerta.periodo.desc()).limit(6).all()

    tendencias = [{"periodo": a.periodo, "total": a.total} for a in alertas_por_periodo]

    return {
        "estudiantes": {
            "total": total_estudiantes,
            "activos": activos
        },
        "alertas": {
            "total": total_alertas,
            "criticas": criticas,
            "pendientes": pendientes,
            "en_proceso": en_proceso,
            "resueltas": resueltas
        },
        "programas": programas_dist,
        "tendencias": tendencias
    }


@router.get("/estados")
async def get_estados(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_dashboard"))
):
    """get student and alert states"""
    estados_est = db.query(
        Estudiante.estado,
        func.count(Estudiante.id).label("total")
    ).group_by(Estudiante.estado).all()

    estados_estudiantes = [{"estado": e.estado.value, "total": e.total} for e in estados_est]

    estados_alert = db.query(
        Alerta.estado_seguimiento,
        func.count(Alerta.id).label("total")
    ).group_by(Alerta.estado_seguimiento).all()

    estados_alertas = [{"estado": e.estado_seguimiento.value, "total": e.total} for e in estados_alert]

    niveles = db.query(
        Alerta.nivel_riesgo,
        func.count(Alerta.id).label("total")
    ).group_by(Alerta.nivel_riesgo).all()

    niveles_riesgo = [{"nivel": n.nivel_riesgo.value, "total": n.total} for n in niveles]

    return {
        "estudiantes": estados_estudiantes,
        "alertas": estados_alertas,
        "niveles_riesgo": niveles_riesgo
    }


@router.get("/recientes")
async def get_recientes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permiso("ver_dashboard")),
    limite: int = Query(10, ge=1, le=50)
):
    """get recent alerts"""
    alertas = db.query(Alerta).order_by(Alerta.created_at.desc()).limit(limite).all()

    return {
        "alertas_recientes": [
            {
                "id": str(a.id),
                "estudiante_id": str(a.estudiante_id),
                "nivel_riesgo": a.nivel_riesgo.value,
                "estado_seguimiento": a.estado_seguimiento.value,
                "periodo": a.periodo,
                "created_at": a.created_at.isoformat()
            }
            for a in alertas
        ]
    }
