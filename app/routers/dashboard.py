"""Router de dashboard y estadísticas"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.estudiante import Estudiante, EstadoEstudiante
from app.models.alerta import Alerta, NivelRiesgo, EstadoSeguimiento
from app.utils.auth import verify_token
from app.utils.permisos import PermisoService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
security = HTTPBearer()


def get_current_user_with_permiso(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")
    return user


@router.get("/resumen")
async def get_resumen(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener resumen general del dashboard"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_dashboard"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    # Contadores básicos
    total_estudiantes = db.query(Estudiante).count()
    activos = db.query(Estudiante).filter(Estudiante.estado == EstadoEstudiante.ACTIVO).count()

    total_alertas = db.query(Alerta).count()
    criticas = db.query(Alerta).filter(Alerta.nivel_riesgo == NivelRiesgo.ROJO).count()
    pendientes = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.PENDIENTE).count()
    en_proceso = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.EN_PROCESO).count()
    resueltas = db.query(Alerta).filter(Alerta.estado_seguimiento == EstadoSeguimiento.RESUELTO).count()

    # Distribución por programa
    programas = db.query(
        Estudiante.programa,
        func.count(Estudiante.id).label("total")
    ).group_by(Estudiante.programa).all()

    programas_dist = [{"programa": p.programa, "total": p.total} for p in programas]

    # Tendencia de alertas por período
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
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener estados de estudiantes y alertas"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_dashboard"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    # Estados de estudiantes
    estados_est = db.query(
        Estudiante.estado,
        func.count(Estudiante.id).label("total")
    ).group_by(Estudiante.estado).all()

    estados_estudiantes = [{"estado": e.estado.value, "total": e.total} for e in estados_est]

    # Estados de seguimiento de alertas
    estados_alert = db.query(
        Alerta.estado_seguimiento,
        func.count(Alerta.id).label("total")
    ).group_by(Alerta.estado_seguimiento).all()

    estados_alertas = [{"estado": e.estado_seguimiento.value, "total": e.total} for e in estados_alert]

    # Niveles de riesgo
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
    current_user: User = Depends(get_current_user_with_permiso),
    limite: int = Query(10, ge=1, le=50)
):
    """Obtener alertas recientes"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_dashboard"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")

    alertas = db.query(Alerta).order_by(Alerta.created_at.desc()).limit(limite).all()

    from app.utils.security import decrypt_data

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