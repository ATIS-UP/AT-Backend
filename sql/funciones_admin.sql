CREATE OR REPLACE FUNCTION purge_all_data() RETURNS void AS $$
BEGIN
    DELETE FROM historial_registros;
    DELETE FROM respuestas_encuestas;
    DELETE FROM actividades;
    DELETE FROM anexos_actividades;
    DELETE FROM artefactos;
    DELETE FROM bienestar_registros;
    DELETE FROM registros_casos_especiales;
    DELETE FROM alertas;
    DELETE FROM actividades_institucionales;
    DELETE FROM encuestas;
    DELETE FROM refresh_tokens;
    DELETE FROM auditoria;
    DELETE FROM user_permisos;
    DELETE FROM rol_permisos;
    DELETE FROM estudiantes;
    DELETE FROM novedades_casos;
    DELETE FROM parametrizacion;
    DELETE FROM users;
    DELETE FROM permisos;
    RAISE NOTICE 'purge_all_data(): todas las tablas purgadas exitosamente';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION purge_keep_essentials() RETURNS void AS $$
BEGIN
    DELETE FROM historial_registros;
    DELETE FROM respuestas_encuestas;
    DELETE FROM actividades;
    DELETE FROM anexos_actividades;
    DELETE FROM artefactos;
    DELETE FROM bienestar_registros;
    DELETE FROM registros_casos_especiales;
    DELETE FROM alertas;
    DELETE FROM actividades_institucionales;
    DELETE FROM refresh_tokens;
    DELETE FROM auditoria;

    RAISE NOTICE 'purge_keep_essentials(): datos transaccionales purgados.';
    RAISE NOTICE 'Conservados: usuarios, permisos, parametros, novedades, plantilla encuesta.';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION purge_for_production() RETURNS void AS $$
BEGIN
    DELETE FROM historial_registros
    WHERE registro_id IN (
        SELECT id FROM registros_casos_especiales
        WHERE estudiante_id IN (
            SELECT id FROM estudiantes WHERE codigo LIKE '202%'
        )
    );
    DELETE FROM registros_casos_especiales
    WHERE estudiante_id IN (
        SELECT id FROM estudiantes WHERE codigo LIKE '202%'
    );
    DELETE FROM respuestas_encuestas
    WHERE estudiante_id IN (
        SELECT id FROM estudiantes WHERE codigo LIKE '202%'
    );
    DELETE FROM estudiantes WHERE codigo LIKE '202%';
    DELETE FROM refresh_tokens;
    DELETE FROM auditoria;
    RAISE NOTICE 'purge_for_production(): datos de desarrollo eliminados.';
    RAISE NOTICE 'Preservados: estudiantes reales, alertas, casos, actividades.';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_db_stats() RETURNS TABLE(tabla text, filas bigint) AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM (
        SELECT 'permisos'::text, COUNT(*)::bigint FROM permisos
        UNION ALL SELECT 'rol_permisos', COUNT(*) FROM rol_permisos
        UNION ALL SELECT 'user_permisos', COUNT(*) FROM user_permisos
        UNION ALL SELECT 'users', COUNT(*) FROM users
        UNION ALL SELECT 'refresh_tokens', COUNT(*) FROM refresh_tokens
        UNION ALL SELECT 'parametrizacion', COUNT(*) FROM parametrizacion
        UNION ALL SELECT 'novedades_casos', COUNT(*) FROM novedades_casos
        UNION ALL SELECT 'encuestas', COUNT(*) FROM encuestas
        UNION ALL SELECT 'respuestas_encuestas', COUNT(*) FROM respuestas_encuestas
        UNION ALL SELECT 'estudiantes', COUNT(*) FROM estudiantes
        UNION ALL SELECT 'alertas', COUNT(*) FROM alertas
        UNION ALL SELECT 'actividades', COUNT(*) FROM actividades
        UNION ALL SELECT 'registros_casos_especiales', COUNT(*) FROM registros_casos_especiales
        UNION ALL SELECT 'historial_registros', COUNT(*) FROM historial_registros
        UNION ALL SELECT 'actividades_institucionales', COUNT(*) FROM actividades_institucionales
        UNION ALL SELECT 'anexos_actividades', COUNT(*) FROM anexos_actividades
        UNION ALL SELECT 'artefactos', COUNT(*) FROM artefactos
        UNION ALL SELECT 'bienestar_registros', COUNT(*) FROM bienestar_registros
        UNION ALL SELECT 'auditoria', COUNT(*) FROM auditoria
    ) stats
    ORDER BY 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION reset_parametrizacion() RETURNS void AS $$
BEGIN
    INSERT INTO parametrizacion (id, clave, valor, descripcion, tipo)
    VALUES (gen_random_uuid(), 'PERIODO_ACTUAL', '2026-1', 'Período académico actual', 'texto')
    ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;

    INSERT INTO parametrizacion (id, clave, valor, descripcion, tipo)
    VALUES (gen_random_uuid(), 'UMBRAL_ROJO', '2.0', 'Promedio mínimo para riesgo rojo', 'numero')
    ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;

    INSERT INTO parametrizacion (id, clave, valor, descripcion, tipo)
    VALUES (gen_random_uuid(), 'UMBRAL_AMARILLO', '3.0', 'Promedio mínimo para riesgo amarillo', 'numero')
    ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;

    INSERT INTO parametrizacion (id, clave, valor, descripcion, tipo)
    VALUES (gen_random_uuid(), 'NOTIFICAR_DOCENTE', 'true', 'Enviar notificación a docentes', 'booleano')
    ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;

    RAISE NOTICE 'reset_parametrizacion(): 4 parámetros restaurados.';
END;
$$ LANGUAGE plpgsql;
