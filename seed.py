"""Script para inicializar la base de datos con datos base (usando SQL directo)"""
from sqlalchemy import text
from app.database import engine
from app.utils.security import hash_password


# Catálogo de permisos
PERMISOS_CATALOGO = [
    # Estudiantes
    ("ver_estudiantes", "Ver Estudiantes", "Ver lista de estudiantes", "estudiantes"),
    ("crear_estudiante", "Crear Estudiante", "Crear nuevos estudiantes", "estudiantes"),
    ("editar_estudiante", "Editar Estudiante", "Editar datos de estudiantes", "estudiantes"),
    ("eliminar_estudiante", "Eliminar Estudiante", "Eliminar estudiantes", "estudiantes"),
    ("ver_historial_estudiante", "Ver Historial", "Ver historial académico", "estudiantes"),

    # Alertas
    ("ver_alertas", "Ver Alertas", "Ver lista de alertas", "alertas"),
    ("crear_alerta", "Crear Alerta", "Crear nuevas alertas", "alertas"),
    ("editar_alerta", "Editar Alerta", "Editar alertas", "alertas"),
    ("eliminar_alerta", "Eliminar Alerta", "Eliminar alertas", "alertas"),
    ("cambiar_estado_alerta", "Cambiar Estado", "Cambiar estado de seguimiento", "alertas"),

    # Actividades
    ("ver_actividades", "Ver Actividades", "Ver actividades", "actividades"),
    ("crear_actividad", "Crear Actividad", "Crear actividades", "actividades"),
    ("editar_actividad", "Editar Actividad", "Editar actividades", "actividades"),
    ("eliminar_actividad", "Eliminar Actividad", "Eliminar actividades", "actividades"),

    # Encuestas
    ("ver_encuestas", "Ver Encuestas", "Ver encuestas", "encuestas"),
    ("crear_encuesta", "Crear Encuesta", "Crear encuestas", "encuestas"),
    ("editar_encuesta", "Editar Encuesta", "Editar encuestas", "encuestas"),
    ("eliminar_encuesta", "Eliminar Encuesta", "Eliminar encuestas", "encuestas"),
    ("responder_encuesta", "Responder Encuesta", "Responder encuestas", "encuestas"),
    ("ver_respuestas_encuesta", "Ver Respuestas", "Ver respuestas de encuestas", "encuestas"),

    # Artefactos
    ("ver_artefactos", "Ver Artefactos", "Ver artefactos", "artefactos"),
    ("subir_artefacto", "Subir Artefacto", "Subir artefactos", "artefactos"),
    ("eliminar_artefacto", "Eliminar Artefacto", "Eliminar artefactos", "artefactos"),

    # Parametrización
    ("ver_parametrizacion", "Ver Parametrización", "Ver parámetros del sistema", "parametrizacion"),
    ("editar_parametrizacion", "Editar Parametrización", "Editar parámetros del sistema", "parametrizacion"),

    # Dashboard
    ("ver_dashboard", "Ver Dashboard", "Ver dashboard y estadísticas", "dashboard"),
    ("ver_reportes", "Ver Reportes", "Ver reportes", "dashboard"),

    # Administración
    ("gestionar_usuarios", "Gestionar Usuarios", "Crear, editar, usuarios", "admin"),
    ("gestionar_permisos", "Gestionar Permisos", "Administrar permisos de usuarios", "admin"),
]


def seed_permisos(conn):
    """Crea el catálogo de permisos"""
    print("Creando permisos...")
    for codigo, nombre, descripcion, categoria in PERMISOS_CATALOGO:
        conn.execute(text("""
            INSERT INTO permisos (id, codigo, nombre, descripcion, categoria)
            SELECT gen_random_uuid(), :codigo, :nombre, :descripcion, :categoria
            WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE codigo = :codigo)
        """), {"codigo": codigo, "nombre": nombre, "descripcion": descripcion, "categoria": categoria})
    print(f"  - {len(PERMISOS_CATALOGO)} permisos creados/verificados")


def seed_usuarios(conn):
    """Crea usuarios iniciales"""
    print("Creando usuarios...")

    usuarios = [
        ("admin@unipamplona.edu.co", "Admin123!", "Administrador Sistema", "ADMINISTRADOR"),
        ("docente@unipamplona.edu.co", "Docente123!", "Docente Principal", "DOCENTE"),
        ("apoyo@unipamplona.edu.co", "Apoyo123!", "Usuario de Apoyo", "APOYO")
    ]

    for email, password, nombre, rol in usuarios:
        password_hash = hash_password(password)
        conn.execute(text("""
            INSERT INTO users (id, email, password_hash, nombre, rol, is_active, is_verified)
            SELECT gen_random_uuid(), :email, :password_hash, :nombre, CAST(:rol AS rolenum), true, true
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = :email)
        """), {"email": email, "password_hash": password_hash, "nombre": nombre, "rol": rol})
        print(f"  - Usuario: {email} ({rol})")

    print("  - Usuarios creados/verificados")


def seed_parametrizacion(conn):
    """Crea parámetros iniciales del sistema"""
    print("Creando parametrización...")

    parametros = [
        ("PERIODO_ACTUAL", "2025-1", "Período académico actual", "texto"),
        ("UMbral_ROJO", "2.0", "Promedio mínimo para riesgo rojo", "numero"),
        ("UMbral_AMARILLO", "3.0", "Promedio mínimo para riesgo amarillo", "numero"),
        ("NOTIFICAR_DOCENTE", "true", "Enviar notificación a docentes", "booleano"),
    ]

    for clave, valor, descripcion, tipo in parametros:
        conn.execute(text("""
            INSERT INTO parametrizacion (id, clave, valor, descripcion, tipo)
            SELECT gen_random_uuid(), :clave, :valor, :descripcion, :tipo
            WHERE NOT EXISTS (SELECT 1 FROM parametrizacion WHERE clave = :clave)
        """), {"clave": clave, "valor": valor, "descripcion": descripcion, "tipo": tipo})

    print(f"  - {len(parametros)} parámetros creados/verificados")


def main():
    """Función principal del seed"""
    print("\n=== INICIALIZANDO BASE DE DATOS ===\n")

    with engine.connect() as conn:
        # Ejecutar seeds
        seed_permisos(conn)
        seed_usuarios(conn)
        seed_parametrizacion(conn)

        # Commit
        conn.commit()

    print("\n=== SEED COMPLETADO ===")
    print("\nUsuarios creados:")
    print("  - admin@unipamplona.edu (password: Admin123!)")
    print("  - docente@unipamplona.edu (password: Docente123!)")
    print("  - apoyo@unipamplona.edu (password: Apoyo123!)")
    print("\n¡Listo para usar!")


if __name__ == "__main__":
    main()