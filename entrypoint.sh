#!/bin/sh
set -eu

log() { printf '[entrypoint %s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }

log "=== Pre-migration state ==="
log "alembic current:"
alembic current || log "(no alembic_version row yet)"
log "alembic heads:"
alembic heads
log "alembic history (last 20 lines):"
alembic history --indicate-current | tail -n 20

log "=== Pending SQL (dry run) ==="
if pending_sql=$(alembic upgrade head --sql 2>/dev/null); then
    echo "$pending_sql" | sed 's/^/    /'
else
    log "(could not generate dry-run SQL)"
fi

log "=== Applying migrations ==="
alembic upgrade head
log "alembic current after upgrade:"
alembic current

log "=== Starting uvicorn ==="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
