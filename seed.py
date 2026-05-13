"""Script para inicializar la base de datos con datos base (usando SQL directo)"""
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import engine
from app.utils.security import hash_password, encrypt_data


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

    # Registros de Casos Especiales
    ("ver_registros_casos", "Ver Registros de Casos", "Ver registros de casos especiales", "casos_especiales"),
    ("crear_registro_caso", "Crear Registro de Caso", "Crear registros de casos especiales", "casos_especiales"),
    ("editar_registro_caso", "Editar Registro de Caso", "Editar registros de casos especiales", "casos_especiales"),
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
        ("apoyo@unipamplona.edu.co", "Apoyo123!", "Usuario de Apoyo", "APOYO"),
        ("pruebas@unipamplona.edu.co", "Pruebas123!", "Usuario de Pruebas", "DOCENTE")
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


def seed_estudiantes_dummy(conn):
    """Crea estudiantes de prueba"""
    print("Creando estudiantes de prueba...")
    
    conn.execute(text("DELETE FROM historial_registros"))
    conn.execute(text("DELETE FROM registros_casos_especiales"))
    conn.execute(text("DELETE FROM estudiantes WHERE codigo LIKE '202%'"))
    print("  - Datos anteriores eliminados")
    
    conn.execute(text("ALTER TABLE estudiantes ALTER COLUMN documento TYPE VARCHAR(200)"))
    conn.execute(text("ALTER TABLE estudiantes ALTER COLUMN telefono TYPE VARCHAR(200)"))
    conn.execute(text("ALTER TABLE estudiantes ALTER COLUMN nombres TYPE VARCHAR(500)"))
    conn.execute(text("ALTER TABLE estudiantes ALTER COLUMN apellidos TYPE VARCHAR(500)"))
    conn.execute(text("ALTER TABLE estudiantes ALTER COLUMN email TYPE VARCHAR(500)"))
    print("  - Tamaños de columnas actualizados para datos encriptados")

    admin = conn.execute(text("SELECT id FROM users WHERE email = 'admin@unipamplona.edu.co'")).fetchone()
    admin_id = str(admin[0]) if admin else None

    estudiantes = [
        {
            "codigo": "20201001",
            "nombres": "Carlos",
            "apellidos": "Mendoza Torres",
            "documento": "1098765432",
            "email": "carlos.mendoza@unipamplona.edu.co",
            "telefono": "3001234567",
            "programa": "Ingeniería de Sistemas",
            "semestre": 8,
            "estado": "ACTIVO",
            "casos": []
        },
        {
            "codigo": "20211002",
            "nombres": "María Fernanda",
            "apellidos": "López Rincón",
            "documento": "1098765433",
            "email": "maria.lopez@unipamplona.edu.co",
            "telefono": "3002345678",
            "programa": "Medicina",
            "semestre": 6,
            "estado": "ACTIVO",
            "casos": [
                {"tipo": "SOCIO_ECONOMICO", "estado": "ACTIVO", "observaciones": "Estudiante con situación económica difícil. Solicita ayuda para materiales."}
            ]
        },
        {
            "codigo": "20221003",
            "nombres": "Juan Andrés",
            "apellidos": "Pérez Gómez",
            "documento": "1098765434",
            "email": "juan.perez@unipamplona.edu.co",
            "telefono": "3003456789",
            "programa": "Ingeniería Civil",
            "semestre": 4,
            "estado": "ACTIVO",
            "casos": [
                {"tipo": "ARTICULADO", "estado": "ACTIVO", "observaciones": "Problemas con asignaturas de matemáticas. Requiere tutorías."},
                {"tipo": "RENDIMIENTO_ACADEMICO", "estado": "CERRADO", "observaciones": "Bajo rendimiento en primer semestre. Ya superó la situación."}
            ]
        },
        {
            "codigo": "20231004",
            "nombres": "Ana Sofía",
            "apellidos": "Ramírez Hernández",
            "documento": "1098765435",
            "email": "ana.ramirez@unipamplona.edu.co",
            "telefono": "3004567890",
            "programa": "Derecho",
            "semestre": 5,
            "estado": "ACTIVO",
            "casos": [
                {"tipo": "SOCIO_ECONOMICO", "estado": "ACTIVO", "observaciones": "Familia en situación vulnerable. Requiere monitoreo."},
                {"tipo": "CONDUCTUAL", "estado": "ACTIVO", "observaciones": "Ha presentado conflictos con compañeros. Se requiere seguimiento."}
            ]
        },
        {
            "codigo": "20241005",
            "nombres": "Pedro Luis",
            "apellidos": "García Sánchez",
            "documento": "1098765436",
            "email": "pedro.garcia@unipamplona.edu.co",
            "telefono": "3005678901",
            "programa": "Ingeniería de Sistemas",
            "semestre": 2,
            "estado": "ACTIVO",
            "casos": [
                {"tipo": "RENDIMIENTO_ACADEMICO", "estado": "PENDIENTE", "observaciones": "Nuevo estudiante. Primer semestre en evaluación."}
            ]
        }
    ]

    for est in estudiantes:
        est_encrypted = {
            "codigo": est["codigo"],
            "nombres": encrypt_data(est["nombres"]),
            "apellidos": encrypt_data(est["apellidos"]),
            "documento": encrypt_data(est["documento"]),
            "email": encrypt_data(est["email"]) if est.get("email") else None,
            "telefono": encrypt_data(est["telefono"]) if est.get("telefono") else None,
            "programa": est["programa"],
            "semestre": est["semestre"],
            "estado": est["estado"]
        }
        
        result = conn.execute(text("""
            INSERT INTO estudiantes (id, codigo, nombres, apellidos, documento, email, telefono, programa, semestre, estado)
            SELECT gen_random_uuid(), :codigo, :nombres, :apellidos, :documento, :email, :telefono, :programa, :semestre, CAST(:estado AS estadoestudiante)
            WHERE NOT EXISTS (SELECT 1 FROM estudiantes WHERE codigo = :codigo)
            RETURNING id
        """), est_encrypted)

        row = result.fetchone()
        if not row:
            existing = conn.execute(text("SELECT id FROM estudiantes WHERE codigo = :codigo"), {"codigo": est["codigo"]}).fetchone()
            estudiante_id = str(existing[0]) if existing else None
        else:
            estudiante_id = str(row[0])

        if estudiante_id and est["casos"]:
            for i, caso in enumerate(est["casos"], 1):
                fecha_creacion = datetime.now() - timedelta(days=30 * (len(est["casos"]) - i))
                historial_accion = "APERTURA"
                if caso["estado"] == "CERRADO":
                    historial_accion = "CIERRE"

                conn.execute(text("""
                    INSERT INTO registros_casos_especiales (id, estudiante_id, tipo, estado, observaciones, responsable_id, responsable_nombre, created_at)
                    SELECT gen_random_uuid(), :estudiante_id, CAST(:tipo AS tiporegistrocaso), CAST(:estado AS estadoregistrocaso), :observaciones, :responsable_id, :responsable_nombre, :created_at
                    WHERE NOT EXISTS (
                        SELECT 1 FROM registros_casos_especiales 
                        WHERE estudiante_id = :estudiante_id AND tipo = CAST(:tipo AS tiporegistrocaso)
                    )
                    RETURNING id
                """), {
                    "estudiante_id": estudiante_id,
                    "tipo": caso["tipo"],
                    "estado": caso["estado"],
                    "observaciones": caso["observaciones"],
                    "responsable_id": admin_id,
                    "responsable_nombre": "Administrador Sistema",
                    "created_at": fecha_creacion
                })

                reg_result = conn.execute(text("SELECT id FROM registros_casos_especiales WHERE estudiante_id = :est_id AND tipo = :tipo"),
                    {"est_id": estudiante_id, "tipo": caso["tipo"]})
                reg_row = reg_result.fetchone()

                if reg_row:
                    conn.execute(text("""
                        INSERT INTO historial_registros (id, registro_id, accion, observaciones, responsable_id, responsable_nombre, created_at)
                        VALUES (gen_random_uuid(), :registro_id, :accion, :observaciones, :responsable_id, :responsable_nombre, :created_at)
                    """), {
                        "registro_id": reg_row[0],
                        "accion": historial_accion,
                        "observaciones": caso["observaciones"],
                        "responsable_id": admin_id,
                        "responsable_nombre": "Administrador Sistema",
                        "created_at": fecha_creacion
                    })

        print(f"  - Estudiante: {est['codigo']} - {est['nombres']} {est['apellidos']} ({len(est['casos'])} casos)")

    print("  - 5 estudiantes creados/verificados")


def main():
    """Función principal del seed"""
    print("\n=== INICIALIZANDO BASE DE DATOS ===\n")

    with engine.connect() as conn:
        # Ejecutar seeds
        seed_permisos(conn)
        seed_usuarios(conn)
        seed_parametrizacion(conn)
        seed_estudiantes_dummy(conn)

        # Commit
        conn.commit()

    print("\n=== SEED COMPLETADO ===")
    print("\nUsuarios creados:")
    print("  - admin@unipamplona.edu.co (password: Admin123!)")
    print("  - docente@unipamplona.edu.co (password: Docente123!)")
    print("  - apoyo@unipamplona.edu.co (password: Apoyo123!)")
    print("\nEstudiantes de prueba:")
    print("  1. Carlos Mendoza (20201001) - SIN casos")
    print("  2. María Fernanda López (20211002) - 1 caso ACTIVO")
    print("  3. Juan Andrés Pérez (20221003) - 2 casos (1 ACTIVO, 1 CERRADO)")
    print("  4. Ana Sofía Ramírez (20231004) - 2 casos ambos ACTIVO")
    print("  5. Pedro Luis García (20241005) - 1 caso PENDIENTE")
    print("\n¡Listo para usar!")


if __name__ == "__main__":
    main()