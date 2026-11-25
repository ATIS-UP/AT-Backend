"""tests for actividad institucional service: busqueda y orden en listar."""

from datetime import UTC as tz_utc, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.services.actividad_institucional_service import (
    ActividadInstitucionalService,
    ahora_colombia,
    orden_proximas_primero,
)


def _make_service():
    """service with a mocked session whose query chain returns itself."""
    db = MagicMock()
    query = MagicMock()
    db.query.return_value = query
    query.options.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = 0
    query.all.return_value = []
    return ActividadInstitucionalService(db), query


def _filtros(query):
    """compile every expression passed to query.filter(): (postgres SQL, bound values)."""
    compilados = [
        call.args[0].compile(dialect=postgresql.dialect())
        for call in query.filter.call_args_list
    ]
    return [(str(c), set(c.params.values())) for c in compilados]


def test_listar_buscar_filtra_por_descripcion_encargado_y_lugar():
    service, query = _make_service()

    service.listar(buscar="taller")

    filtros = _filtros(query)
    assert len(filtros) == 1
    sql, valores = filtros[0]
    assert sql.count("ILIKE") == 3
    assert "descripcion" in sql
    assert "encargado" in sql
    assert "lugar_enlace" in sql
    assert valores == {"%taller%"}


def test_listar_buscar_se_aplica_antes_del_count():
    service, query = _make_service()
    orden = []
    query.filter.side_effect = lambda *a: orden.append("filter") or query
    query.count.side_effect = lambda: orden.append("count") or 0

    service.listar(buscar="taller")

    assert orden == ["filter", "count"]


@pytest.mark.parametrize("buscar", [None, "", "   "])
def test_listar_sin_busqueda_no_agrega_filtro(buscar):
    service, query = _make_service()

    service.listar(buscar=buscar)

    query.filter.assert_not_called()


def test_listar_buscar_escapa_comodines_like():
    service, query = _make_service()

    service.listar(buscar="50%_")

    _, valores = _filtros(query)[0]
    assert valores == {"%50\\%\\_%"}


def test_listar_buscar_recorta_espacios():
    service, query = _make_service()

    service.listar(buscar="  taller  ")

    _, valores = _filtros(query)[0]
    assert valores == {"%taller%"}


def test_listar_combina_busqueda_con_tipo_y_estado():
    service, query = _make_service()

    service.listar(estado="CREADA", tipo="CLASE", buscar="taller")

    assert query.filter.call_count == 3


# --- orden: próximas primero, luego pasadas ---

def _sql(expr):
    return str(expr.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_ahora_colombia_es_utc_menos_5_sin_tzinfo():
    ahora = ahora_colombia()
    esperado = datetime.now(tz_utc).replace(tzinfo=None) - timedelta(hours=5)
    assert ahora.tzinfo is None
    assert abs((ahora - esperado).total_seconds()) < 5


def test_orden_proximas_primero_estructura():
    ahora = datetime(2026, 11, 25, 14, 30)
    grupo, proximas, pasadas, creacion, desempate = [_sql(e) for e in orden_proximas_primero(ahora)]

    # grupo 0 = no terminada y no cancelada/finalizada
    assert "fecha_fin >= '2026-11-25 14:30:00'" in grupo
    assert "NOT IN ('CANCELADA', 'FINALIZADA')" in grupo
    assert "THEN 0 ELSE 1" in grupo
    # próximas: la más cercana primero; pasadas: la más reciente primero
    assert proximas.endswith("ASC") and "fecha_inicio" in proximas
    assert pasadas == "actividades_institucionales.fecha_inicio DESC"
    assert creacion == "actividades_institucionales.created_at DESC"
    assert desempate == "actividades_institucionales.id"


def test_listar_ordena_con_hora_de_colombia():
    service, query = _make_service()
    fija = datetime(2026, 11, 25, 8, 0)

    with patch("app.services.actividad_institucional_service.ahora_colombia", return_value=fija):
        service.listar()

    (args, _), = query.order_by.call_args_list
    assert "'2026-11-25 08:00:00'" in _sql(args[0])
