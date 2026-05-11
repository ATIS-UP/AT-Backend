"""Servicio de permisos y verificación de acceso"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.user import User, Permiso, UserPermiso, RolEnum


PERMISOS_BASE_POR_ROL = {
    RolEnum.ADMINISTRADOR: "*",  # all permissions
    RolEnum.DOCENTE: "*",         # all permissions
    RolEnum.APOYO: [              # limited permissions for support role
        "ver_estudiantes",
        "crear_estudiante",
        "editar_estudiante",
        "ver_alertas",
        "crear_alerta",
        "cambiar_estado_alerta",
        "ver_actividades",
        "crear_actividad",
        "ver_dashboard",
    ]
}


class PermisoService:
    """Servicio para verificar permisos de usuarios"""

    @staticmethod
    def tiene_permiso(db: Session, usuario: User, permiso_codigo: str) -> bool:
        """
        Verifica si un usuario tiene un permiso específico
        1. Si es ADMIN o DOCENTE, tiene todos los permisos
        2. Si es APOYO, verificar permisos base + overrides
        """
        # ADMIN y DOCENTE tienen todos los permisos
        if usuario.rol in [RolEnum.ADMINISTRADOR, RolEnum.DOCENTE]:
            return True

        # APOYO: verificar permisos base
        permisos_base = PERMISOS_BASE_POR_ROL.get(RolEnum.APOYO, [])
        if permiso_codigo in permisos_base:
            return True

        # Verificar overrides del usuario
        override = db.query(UserPermiso).filter(
            UserPermiso.user_id == usuario.id,
            UserPermiso.permiso_codigo == permiso_codigo
        ).first()

        if override:
            return override.tiene_permiso

        return False

    @staticmethod
    def get_permisos_usuario(db: Session, usuario: User) -> List[str]:
        """
        Obtiene la lista de permisos activos de un usuario
        """
        permisos = []

        # ADMIN y DOCENTE tienen todos los permisos del catálogo
        if usuario.rol in [RolEnum.ADMINISTRADOR, RolEnum.DOCENTE]:
            todos_permisos = db.query(Permiso.codigo).all()
            return [p.codigo for p in todos_permisos]

        # APOYO: permisos base + overrides
        permisos_base = PERMISOS_BASE_POR_ROL.get(RolEnum.APOYO, [])
        permisos = list(permisos_base) if permisos_base else []

        # Agregar overrides
        overrides = db.query(UserPermiso).filter(
            UserPermiso.user_id == usuario.id
        ).all()

        for override in overrides:
            if override.tiene_permiso and override.permiso_codigo not in permisos:
                permisos.append(override.permiso_codigo)
            elif not override.tiene_permiso and override.permiso_codigo in permisos:
                permisos.remove(override.permiso_codigo)

        return permisos

    @staticmethod
    def set_permiso_usuario(db: Session, user_id: str, permiso_codigo: str, tiene_permiso: bool) -> UserPermiso:
        """Establece un override de permiso para un usuario"""
        # Verificar si ya existe el override
        override = db.query(UserPermiso).filter(
            UserPermiso.user_id == user_id,
            UserPermiso.permiso_codigo == permiso_codigo
        ).first()

        if override:
            override.tiene_permiso = tiene_permiso
        else:
            override = UserPermiso(
                user_id=user_id,
                permiso_codigo=permiso_codigo,
                tiene_permiso=tiene_permiso
            )
            db.add(override)

        db.commit()
        db.refresh(override)
        return override

    @staticmethod
    def get_todos_permisos(db: Session) -> List[Permiso]:
        """Obtiene todos los permisos del catálogo"""
        return db.query(Permiso).order_by(Permiso.categoria, Permiso.nombre).all()

    @staticmethod
    def get_permisos_por_categoria(db: Session) -> dict:
        """Agrupa todos los permisos por categoría"""
        permisos = PermisoService.get_todos_permisos(db)
        categorias = {}
        for permiso in permisos:
            if permiso.categoria not in categorias:
                categorias[permiso.categoria] = []
            categorias[permiso.categoria].append({
                "codigo": permiso.codigo,
                "nombre": permiso.nombre,
                "descripcion": permiso.descripcion
            })
        return categorias