"""Seed mÃ­nimo: purga BD y crea solo datos esenciales para operar"""
import uuid
from datetime import datetime
from sqlalchemy import text
from app.database import engine
from app.utils.security import hash_password, encrypt_data


PERMISOS_CATALOGO = [
    ("ver_estudiantes", "Ver Estudiantes", "Ver lista de estudiantes", "estudiantes"),
    ("crear_estudiante", "Crear Estudiante", "Crear nuevos estudiantes", "estudiantes"),
    ("editar_estudiante", "Editar Estudiante", "Editar datos de estudiantes", "estudiantes"),
    ("eliminar_estudiante", "Eliminar Estudiante", "Eliminar estudiantes", "estudiantes"),
    ("ver_historial_estudiante", "Ver Historial", "Ver historial acadÃ©mico", "estudiantes"),
    ("ver_alertas", "Ver Alertas", "Ver lista de alertas", "alertas"),
    ("crear_alerta", "Crear Alerta", "Crear nuevas alertas", "alertas"),
    ("editar_alerta", "Editar Alerta", "Editar alertas", "alertas"),
    ("eliminar_alerta", "Eliminar Alerta", "Eliminar alertas", "alertas"),
    ("cambiar_estado_alerta", "Cambiar Estado", "Cambiar estado de seguimiento", "alertas"),
    ("ver_actividades", "Ver Actividades", "Ver actividades", "actividades"),
    ("crear_actividad", "Crear Actividad", "Crear actividades", "actividades"),
    ("editar_actividad", "Editar Actividad", "Editar actividades", "actividades"),
    ("eliminar_actividad", "Eliminar Actividad", "Eliminar actividades", "actividades"),
    ("ver_encuestas", "Ver Encuestas", "Ver encuestas", "encuestas"),
    ("crear_encuesta", "Crear Encuesta", "Crear encuestas", "encuestas"),
    ("editar_encuesta", "Editar Encuesta", "Editar encuestas", "encuestas"),
    ("eliminar_encuesta", "Eliminar Encuesta", "Eliminar encuestas", "encuestas"),
    ("responder_encuesta", "Responder Encuesta", "Responder encuestas", "encuestas"),
    ("ver_respuestas_encuesta", "Ver Respuestas", "Ver respuestas de encuestas", "encuestas"),
    ("ver_artefactos", "Ver Artefactos", "Ver artefactos", "artefactos"),
    ("subir_artefacto", "Subir Artefacto", "Subir artefactos", "artefactos"),
    ("eliminar_artefacto", "Eliminar Artefacto", "Eliminar artefactos", "artefactos"),
    ("ver_parametrizacion", "Ver ParametrizaciÃ³n", "Ver parÃ¡metros del sistema", "parametrizacion"),
    ("editar_parametrizacion", "Editar ParametrizaciÃ³n", "Editar parÃ¡metros del sistema", "parametrizacion"),
    ("ver_dashboard", "Ver Dashboard", "Ver dashboard y estadÃ­sticas", "dashboard"),
    ("ver_reportes", "Ver Reportes", "Ver reportes", "dashboard"),
    ("gestionar_usuarios", "Gestionar Usuarios", "Crear, editar, usuarios", "admin"),
    ("gestionar_permisos", "Gestionar Permisos", "Administrar permisos de usuarios", "admin"),
    ("ver_registros_casos", "Ver Registros de Casos", "Ver registros de casos especiales", "casos_especiales"),
    ("crear_registro_caso", "Crear Registro de Caso", "Crear registros de casos especiales", "casos_especiales"),
    ("editar_registro_caso", "Editar Registro de Caso", "Editar registros de casos especiales", "casos_especiales"),
]

PERMISOS_ADMIN = [p[0] for p in PERMISOS_CATALOGO]

PERMISOS_DOCENTE = [
    "ver_estudiantes", "crear_estudiante", "editar_estudiante", "ver_historial_estudiante",
    "ver_alertas", "crear_alerta", "editar_alerta", "cambiar_estado_alerta",
    "ver_actividades", "crear_actividad", "editar_actividad",
    "ver_encuestas", "responder_encuesta",
    "ver_artefactos",
    "ver_dashboard", "ver_reportes",
    "ver_parametrizacion",
    "ver_registros_casos", "crear_registro_caso", "editar_registro_caso",
]

PERMISOS_APOYO = [
    "ver_estudiantes", "ver_historial_estudiante",
    "ver_alertas", "crear_alerta", "cambiar_estado_alerta",
    "ver_actividades", "crear_actividad",
    "ver_encuestas", "responder_encuesta",
    "ver_artefactos", "subir_artefacto",
    "ver_dashboard",
    "ver_registros_casos", "crear_registro_caso",
]


NOVEDADES_POR_TIPO = {
    "RENDIMIENTO_ACADEMICO": [
        ("Bajo rendimiento acumulado", "Estudiantes que entran en prueba acadÃ©mica o tienen un promedio por debajo del estÃ¡ndar institucional."),
        ("PÃ©rdida recurrente de asignaturas", "Especialmente cuando se trata de materias del nÃºcleo bÃ¡sico."),
        ("Inasistencia injustificada", "Ausencias reiteradas que superan el porcentaje permitido o que muestran un patrÃ³n de desconexiÃ³n."),
        ("Falta de competencias bÃ¡sicas", "Dificultades marcadas en lectoescritura, razonamiento lÃ³gico o mÃ©todos de estudio."),
        ("Otra", None),
    ],
    "PSICOSOCIAL": [
        ("Crisis emocionales o ansiedad", "Manifestaciones de estrÃ©s elevado, depresiÃ³n o cambios drÃ¡sticos en el comportamiento."),
        ("Problemas familiares", "Duelos, separaciones o conflictos en el hogar que interfieren con la concentraciÃ³n del estudiante."),
        ("Consumo de sustancias", "Casos detectados o sospechas de abuso de alcohol o sustancias psicoactivas."),
        ("Dificultades de adaptaciÃ³n", "ComÃºn en estudiantes que provienen de otras regiones (forÃ¡neos) y presentan problemas para integrarse al entorno universitario o a la ciudad."),
    ],
    "SOCIO_ECONOMICO": [
        ("Inestabilidad financiera", "Dificultades para cubrir el pago de matrÃ­cula, materiales de estudio o transporte."),
        ("Inseguridad alimentaria", "Estudiantes que no cuentan con los recursos para una nutriciÃ³n adecuada durante la jornada acadÃ©mica."),
        ("Carga laboral excesiva", "Estudiantes que trabajan jornadas extensas que les impiden cumplir con sus compromisos acadÃ©micos."),
    ],
    "INSTITUCIONAL_VOCACIONAL": [
        ("Inconformidad con la carrera", "Dudas sobre la elecciÃ³n profesional o falta de motivaciÃ³n con el plan de estudios."),
        ("Desconocimiento de servicios", "Estudiantes que requieren orientaciÃ³n sobre becas, subsidios o apoyos institucionales y no saben cÃ³mo acceder a ellos."),
    ],
    "OTRO": [
        ("Otra", None),
    ],
}

PARAMETROS = [
    ("PERIODO_ACTUAL", "2026-1", "PerÃ­odo acadÃ©mico actual", "texto"),
    ("UMbral_ROJO", "2.0", "Promedio mÃ­nimo para riesgo rojo", "numero"),
    ("UMbral_AMARILLO", "3.0", "Promedio mÃ­nimo para riesgo amarillo", "numero"),
    ("NOTIFICAR_DOCENTE", "true", "Enviar notificaciÃ³n a docentes", "booleano"),
]

PLANTILLA_PREGUNTAS = [
    {"id": 1, "texto": "Estrato socioeconÃ³mico", "tipo": "opcion_multiple",
     "opciones": ["1", "2", "3", "4", "5", "6"], "requerida": True, "campo": "estrato", "editable": True},
    {"id": 2, "texto": "GÃ©nero", "tipo": "opcion_multiple",
     "opciones": ["H", "M", "OTRO"], "requerida": True, "campo": "genero", "editable": True},
    {"id": 3, "texto": "Procedencia", "tipo": "opcion_multiple",
     "opciones": ["LOCAL", "FORANEO"], "requerida": True, "campo": "procedencia", "editable": True},
    {"id": 4, "texto": "Ingreso familiar mensual ($)", "tipo": "texto_libre",
     "requerida": False, "campo": "ingreso_familiar", "editable": True},
    {"id": 5, "texto": "Correo electrÃ³nico", "tipo": "texto_libre",
     "requerida": False, "campo": "email", "editable": True},
    {"id": 6, "texto": "TelÃ©fono de contacto", "tipo": "texto_libre",
     "requerida": False, "campo": "telefono", "editable": True},
    {"id": 7, "texto": "Programa acadÃ©mico", "tipo": "texto_libre",
     "requerida": True, "campo": "programa", "editable": False},
    {"id": 8, "texto": "Semestre actual", "tipo": "opcion_multiple",
     "opciones": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
     "requerida": True, "campo": "semestre", "editable": False},
]


def purge_all_data(conn):
    print("Purgando todos los datos...")
    conn.execute(text("DELETE FROM historial_registros"))
    conn.execute(text("DELETE FROM respuestas_encuestas"))
    conn.execute(text("DELETE FROM actividades"))
    conn.execute(text("DELETE FROM anexos_actividades"))
    conn.execute(text("DELETE FROM artefactos"))
    conn.execute(text("DELETE FROM bienestar_registros"))
    conn.execute(text("DELETE FROM registros_casos_especiales"))
    conn.execute(text("DELETE FROM alertas"))
    conn.execute(text("DELETE FROM actividades_institucionales"))
    conn.execute(text("DELETE FROM encuestas"))
    conn.execute(text("DELETE FROM refresh_tokens"))
    conn.execute(text("DELETE FROM auditoria"))
    conn.execute(text("DELETE FROM user_permisos"))
    conn.execute(text("DELETE FROM rol_permisos"))
    conn.execute(text("DELETE FROM estudiantes"))
    conn.execute(text("DELETE FROM novedades_casos"))
    conn.execute(text("DELETE FROM parametrizacion"))
    conn.execute(text("DELETE FROM users"))
    conn.execute(text("DELETE FROM permisos"))
    print("  - 19 tablas purgadas exitosamente")


def seed_permisos(conn):
    print("Creando permisos...")
    for codigo, nombre, descripcion, categoria in PERMISOS_CATALOGO:
        conn.execute(text("""
            INSERT INTO permisos (id, codigo, nombre, descripcion, categoria)
            SELECT gen_random_uuid(), :codigo, :nombre, :descripcion, :categoria
            WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE codigo = :codigo)
        """), {"codigo": codigo, "nombre": nombre, "descripcion": descripcion, "categoria": categoria})
    print(f"  - {len(PERMISOS_CATALOGO)} permisos creados/verificados")


def seed_rol_permisos(conn):
    print("Asignando permisos por rol...")
    roles = [
        ("ADMINISTRADOR", PERMISOS_ADMIN),
        ("DOCENTE", PERMISOS_DOCENTE),
        ("APOYO", PERMISOS_APOYO),
    ]
    total = 0
    for rol, permisos in roles:
        for codigo in permisos:
            conn.execute(text("""
                INSERT INTO rol_permisos (id, rol, permiso_codigo, tiene_permiso)
                SELECT gen_random_uuid(), CAST(:rol AS rolenum), :codigo, true
                WHERE NOT EXISTS (
                    SELECT 1 FROM rol_permisos
                    WHERE rol = CAST(:rol AS rolenum) AND permiso_codigo = :codigo
                )
            """), {"rol": rol, "codigo": codigo})
            total += 1
    print(f"  - {total} asignaciones rol-permiso creadas/verificadas")


def seed_usuarios(conn):
    print("Creando usuarios...")
    usuarios = [
        ("admin@unipamplona.edu.co", "Admin123!", "Administrador Sistema", "ADMINISTRADOR"),
        ("docente@unipamplona.edu.co", "Docente123!", "Docente Principal", "DOCENTE"),
        ("apoyo@unipamplona.edu.co", "Apoyo123!", "Usuario de Apoyo", "APOYO"),
    ]
    for email, password, nombre, rol in usuarios:
        password_hash = hash_password(password)
        conn.execute(text("""
            INSERT INTO users (id, email, password_hash, nombre, rol, is_active, is_verified)
            SELECT gen_random_uuid(), :email, :password_hash, :nombre, CAST(:rol AS rolenum), true, true
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = :email)
        """), {"email": email, "password_hash": password_hash, "nombre": nombre, "rol": rol})
        print(f"  - Usuario: {email} ({rol})")
    print("  - 3 usuarios creados/verificados")


def seed_parametrizacion(conn):
    print("Creando parametrizaciÃ³n...")
    for clave, valor, descripcion, tipo in PARAMETROS:
        conn.execute(text("""
            INSERT INTO parametrizacion (id, clave, valor, descripcion, tipo)
            SELECT gen_random_uuid(), :clave, :valor, :descripcion, :tipo
            WHERE NOT EXISTS (SELECT 1 FROM parametrizacion WHERE clave = :clave)
        """), {"clave": clave, "valor": valor, "descripcion": descripcion, "tipo": tipo})
    print(f"  - {len(PARAMETROS)} parÃ¡metros creados/verificados")


def seed_novedades(conn):
    print("Creando novedades de casos especiales...")
    total = 0
    for tipo_caso, novedades in NOVEDADES_POR_TIPO.items():
        for idx, (nombre, descripcion) in enumerate(novedades, 1):
            conn.execute(text("""
                INSERT INTO novedades_casos (id, tipo_caso, nombre, descripcion, activo, orden)
                SELECT gen_random_uuid(), :tipo_caso, :nombre, :descripcion, true, :orden
                WHERE NOT EXISTS (
                    SELECT 1 FROM novedades_casos
                    WHERE tipo_caso = :tipo_caso AND nombre = :nombre
                )
            """), {"tipo_caso": tipo_caso, "nombre": nombre, "descripcion": descripcion, "orden": idx})
            total += 1
    print(f"  - {total} novedades creadas/verificadas")


def seed_plantilla_encuesta(conn):
    print("Creando plantilla de encuesta...")
    admin = conn.execute(text("SELECT id FROM users WHERE email = 'admin@unipamplona.edu.co'")).fetchone()
    admin_id = str(admin[0]) if admin else None

    conn.execute(text("""
        INSERT INTO encuestas (id, titulo, descripcion, preguntas, estado, periodo, es_publica)
        SELECT gen_random_uuid(), :titulo, :descripcion, :preguntas::jsonb, 'BORRADOR', NULL, false
        WHERE NOT EXISTS (
            SELECT 1 FROM encuestas WHERE titulo = :titulo AND estado = 'BORRADOR'
        )
    """), {
        "titulo": "ActualizaciÃ³n de Datos Estudiantiles",
        "descripcion": "Completa o actualiza tus datos personales y acadÃ©micos para mantener la informaciÃ³n al dÃ­a.",
        "preguntas": str(PLANTILLA_PREGUNTAS),
    })

    if admin_id:
        encuesta = conn.execute(text(
            "SELECT id FROM encuestas WHERE titulo = 'ActualizaciÃ³n de Datos Estudiantiles' AND estado = 'BORRADOR'"
        )).fetchone()
        if encuesta:
            conn.execute(text("""
                INSERT INTO auditoria (id, usuario_id, accion, entidad, entidad_id, detalles, estado)
                SELECT gen_random_uuid(), :usuario_id, 'CREAR', 'Encuesta', :entidad_id, :detalles::jsonb, 'EXITOSO'
                WHERE NOT EXISTS (
                    SELECT 1 FROM auditoria WHERE entidad_id = :entidad_id2 AND accion = 'CREAR'
                )
            """), {
                "usuario_id": admin_id,
                "entidad_id": str(encuesta[0]),
                "detalles": '{"titulo": "ActualizaciÃ³n de Datos Estudiantiles", "num_preguntas": 8, "es_plantilla": true}',
                "entidad_id2": str(encuesta[0]),
            })

    print("  - 1 plantilla de encuesta creada/verificada")


def main():
    print("\n=== SEED MÃNIMO ===\n")

    with engine.connect() as conn:
        purge_all_data(conn)
        conn.commit()

        seed_permisos(conn)
        seed_rol_permisos(conn)
        seed_usuarios(conn)
        seed_parametrizacion(conn)
        seed_novedades(conn)
        seed_plantilla_encuesta(conn)

        conn.commit()

    print("\n=== SEED MÃNIMO COMPLETADO ===")
    print("\nUsuarios creados:")
    print("  - admin@unipamplona.edu.co (password: Admin123!)")
    print("  - docente@unipamplona.edu.co (password: Docente123!)")
    print("  - apoyo@unipamplona.edu.co (password: Apoyo123!)")
    print("\nDatos creados:")
    print(f"  - {len(PERMISOS_CATALOGO)} permisos")
    print(f"  - Asignaciones por rol (ADMIN: 32, DOCENTE: {len(PERMISOS_DOCENTE)}, APOYO: {len(PERMISOS_APOYO)})")
    print("  - 3 usuarios")
    print("  - 4 parÃ¡metros del sistema")
    print(f"  - {sum(len(v) for v in NOVEDADES_POR_TIPO.values())} novedades de casos")
    print("  - 1 plantilla de encuesta (BORRADOR)")
    print("\nÃnica opciÃ³n antes de ejecutar: editar PERIODO_ACTUAL en seed_minimo.py lÃ­nea 212")
    print("  si el periodo actual no es 2026-1\n")
    print("Â¡Listo para usar!")


if __name__ == "__main__":
    main()
