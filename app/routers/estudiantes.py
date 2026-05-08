"""Router de estudiantes"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.estudiante import Estudiante, Inscripcion, Materia
from app.schemas.estudiante import (
    EstudianteCreate, EstudianteUpdate, EstudianteResponse,
    EstudianteListResponse, HistorialAcademico, InscripcionResponse
)
from app.utils.auth import verify_token
from app.utils.security import encrypt_data, decrypt_data
from app.utils.permisos import PermisoService
from app.utils.audit import AuditService

router = APIRouter(prefix="/api/estudiantes", tags=["estudiantes"])
security = HTTPBearer()


def get_current_user_with_permiso(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependency que verifica token y retorna usuario"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo"
        )
    return user


@router.get("", response_model=EstudianteListResponse)
async def list_estudiantes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    buscar: str = Query(None),
    estado: str = Query(None),
    programa: str = Query(None)
):
    """Listar estudiantes con paginación y filtros"""
    # Verificar permiso
    if not PermisoService.tiene_permiso(db, current_user, "ver_estudiantes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver estudiantes"
        )

    query = db.query(Estudiante)

    # Filtros
    if buscar:
        query = query.filter(
            (Estudiante.codigo.ilike(f"%{buscar}%")) |
            (Estudiante.nombres.ilike(f"%{buscar}%")) |
            (Estudiante.apellidos.ilike(f"%{buscar}%"))
        )
    if estado:
        query = query.filter(Estudiante.estado == estado)
    if programa:
        query = query.filter(Estudiante.programa.ilike(f"%{programa}%"))

    # Total
    total = query.count()

    # Paginar
    estudiantes = query.order_by(Estudiante.apellidos).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    # Desencriptar datos para respuesta
    resultados = []
    for est in estudiantes:
        resultados.append(EstudianteResponse(
            id=str(est.id),
            codigo=est.codigo,
            nombres=decrypt_data(est.nombres),
            apellidos=decrypt_data(est.apellidos),
            email=decrypt_data(est.email) if est.email else None,
            documento=decrypt_data(est.documento) if est.documento else None,
            telefono=decrypt_data(est.telefono) if est.telefono else None,
            programa=est.programa,
            semestre=est.semestre,
            promedio_general=float(decrypt_data(str(est.promedio_general))) if est.promedio_general else None,
            promedio_acumulado=float(decrypt_data(str(est.promedio_acumulado))) if est.promedio_acumulado else None,
            estado=est.estado.value,
            created_at=est.created_at,
            updated_at=est.updated_at
        ))

    return EstudianteListResponse(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        estudiantes=resultados
    )


@router.get("/{estudiante_id}", response_model=EstudianteResponse)
async def get_estudiante(
    estudiante_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener un estudiante por ID"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_estudiantes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver estudiantes"
        )

    est = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )

    return EstudianteResponse(
        id=str(est.id),
        codigo=est.codigo,
        nombres=decrypt_data(est.nombres),
        apellidos=decrypt_data(est.apellidos),
        email=decrypt_data(est.email) if est.email else None,
        documento=decrypt_data(est.documento) if est.documento else None,
        telefono=decrypt_data(est.telefono) if est.telefono else None,
        programa=est.programa,
        semestre=est.semestre,
        promedio_general=float(decrypt_data(str(est.promedio_general))) if est.promedio_general else None,
        promedio_acumulado=float(decrypt_data(str(est.promedio_acumulado))) if est.promedio_acumulado else None,
        estado=est.estado.value,
        created_at=est.created_at,
        updated_at=est.updated_at
    )


@router.post("", response_model=EstudianteResponse, status_code=status.HTTP_201_CREATED)
async def create_estudiante(
    estudiante_data: EstudianteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Crear un nuevo estudiante"""
    if not PermisoService.tiene_permiso(db, current_user, "crear_estudiante"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para crear estudiantes"
        )

    # Verificar que el código no exista
    existente = db.query(Estudiante).filter(Estudiante.codigo == estudiante_data.codigo).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un estudiante con este código"
        )

    # Encriptar datos sensibles
    nuevo = Estudiante(
        codigo=estudiante_data.codigo,
        nombres=encrypt_data(estudiante_data.nombres),
        apellidos=encrypt_data(estudiante_data.apellidos),
        email=encrypt_data(estudiante_data.email) if estudiante_data.email else None,
        documento=encrypt_data(estudiante_data.documento) if estudiante_data.documento else None,
        telefono=encrypt_data(estudiante_data.telefono) if estudiante_data.telefono else None,
        programa=estudiante_data.programa,
        semestre=estudiante_data.semestre,
        promedio_general=encrypt_data(str(estudiante_data.promedio_general)) if estudiante_data.promedio_general else None,
        promedio_acumulado=encrypt_data(str(estudiante_data.promedio_acumulado)) if estudiante_data.promedio_acumulado else None,
        estado=estudiante_data.estado
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # Auditoría
    AuditService.log_crear(
        db, str(current_user.id), "Estudiante", str(nuevo.id),
        {"codigo": nuevo.codigo, "nombres": decrypt_data(nuevo.nombres)},
        request.client.host
    )

    return EstudianteResponse(
        id=str(nuevo.id),
        codigo=nuevo.codigo,
        nombres=decrypt_data(nuevo.nombres),
        apellidos=decrypt_data(nuevo.apellidos),
        email=decrypt_data(nuevo.email) if nuevo.email else None,
        documento=decrypt_data(nuevo.documento) if nuevo.documento else None,
        telefono=decrypt_data(nuevo.telefono) if nuevo.telefono else None,
        programa=nuevo.programa,
        semestre=nuevo.semestre,
        promedio_general=float(decrypt_data(str(nuevo.promedio_general))) if nuevo.promedio_general else None,
        promedio_acumulado=float(decrypt_data(str(nuevo.promedio_acumulado))) if nuevo.promedio_acumulado else None,
        estado=nuevo.estado.value,
        created_at=nuevo.created_at,
        updated_at=nuevo.updated_at
    )


@router.put("/{estudiante_id}", response_model=EstudianteResponse)
async def update_estudiante(
    estudiante_id: str,
    estudiante_data: EstudianteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Actualizar un estudiante"""
    if not PermisoService.tiene_permiso(db, current_user, "editar_estudiante"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar estudiantes"
        )

    est = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )

    # Datos anteriores para auditoría
    datos_anteriores = {
        "nombres": decrypt_data(est.nombres),
        "apellidos": decrypt_data(est.apellidos),
        "programa": est.programa
    }

    # Actualizar campos
    update_data = estudiante_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            # Encriptar campos sensibles
            if key in ["nombres", "apellidos", "email", "documento", "telefono"]:
                setattr(est, key, encrypt_data(value))
            elif key in ["promedio_general", "promedio_acumulado"]:
                setattr(est, key, encrypt_data(str(value)) if value else None)
            else:
                setattr(est, key, value)

    db.commit()
    db.refresh(est)

    # Auditoría
    AuditService.log_actualizar(
        db, str(current_user.id), "Estudiante", str(est.id),
        datos_anteriores, update_data, request.client.host
    )

    return EstudianteResponse(
        id=str(est.id),
        codigo=est.codigo,
        nombres=decrypt_data(est.nombres),
        apellidos=decrypt_data(est.apellidos),
        email=decrypt_data(est.email) if est.email else None,
        documento=decrypt_data(est.documento) if est.documento else None,
        telefono=decrypt_data(est.telefono) if est.telefono else None,
        programa=est.programa,
        semestre=est.semestre,
        promedio_general=float(decrypt_data(str(est.promedio_general))) if est.promedio_general else None,
        promedio_acumulado=float(decrypt_data(str(est.promedio_acumulado))) if est.promedio_acumulado else None,
        estado=est.estado.value,
        created_at=est.created_at,
        updated_at=est.updated_at
    )


@router.delete("/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_estudiante(
    estudiante_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Eliminar un estudiante"""
    if not PermisoService.tiene_permiso(db, current_user, "eliminar_estudiante"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar estudiantes"
        )

    est = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )

    # Datos para auditoría
    datos_eliminados = {
        "codigo": est.codigo,
        "nombres": decrypt_data(est.nombres)
    }

    db.delete(est)
    db.commit()

    # Auditoría
    AuditService.log_eliminar(
        db, str(current_user.id), "Estudiante", estudiante_id,
        datos_eliminados, request.client.host
    )

    return None


@router.get("/{estudiante_id}/historial", response_model=HistorialAcademico)
async def get_historial(
    estudiante_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permiso)
):
    """Obtener historial académico de un estudiante"""
    if not PermisoService.tiene_permiso(db, current_user, "ver_estudiantes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver estudiantes"
        )

    est = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )

    # Obtener inscripciones
    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.estudiante_id == estudiante_id
    ).all()

    return HistorialAcademico(
        estudiante=EstudianteResponse(
            id=str(est.id),
            codigo=est.codigo,
            nombres=decrypt_data(est.nombres),
            apellidos=decrypt_data(est.apellidos),
            email=decrypt_data(est.email) if est.email else None,
            documento=decrypt_data(est.documento) if est.documento else None,
            telefono=decrypt_data(est.telefono) if est.telefono else None,
            programa=est.programa,
            semestre=est.semestre,
            promedio_general=float(decrypt_data(str(est.promedio_general))) if est.promedio_general else None,
            promedio_acumulado=float(decrypt_data(str(est.promedio_acumulado))) if est.promedio_acumulado else None,
            estado=est.estado.value,
            created_at=est.created_at,
            updated_at=est.updated_at
        ),
        inscripciones=[
            InscripcionResponse(
                id=str(ins.id),
                estudiante_id=str(ins.estudiante_id),
                materia_id=str(ins.materia_id),
                materia=None,
                periodo=ins.periodo,
                nota_final=float(decrypt_data(str(ins.nota_final))) if ins.nota_final else None,
                estado=ins.estado.value
            )
            for ins in inscripciones
        ],
        promedio_general=float(decrypt_data(str(est.promedio_general))) if est.promedio_general else None
    )