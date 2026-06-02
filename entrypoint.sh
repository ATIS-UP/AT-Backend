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

log "=== Validating alembic state ==="
HEAD_COUNT=$(alembic heads 2>/dev/null | grep -c "(head)" || true)
if [ "$HEAD_COUNT" -gt 1 ]; then
    log "FATAL: $HEAD_COUNT alembic heads detected. Manual fix required."
    alembic heads
    exit 1
fi
if [ -f alembic/EXPECTED_HEAD ]; then
    EXPECTED=$(cat alembic/EXPECTED_HEAD | tr -d '[:space:]')
    ACTUAL=$(alembic heads 2>/dev/null | grep "(head)" | head -1 | awk '{print $1}' | tr -d '[:space:]')
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        log "FATAL: head drift detected (expected=$EXPECTED, actual=$ACTUAL)."
        exit 1
    fi
    log "OK: head matches EXPECTED_HEAD ($ACTUAL)"
else
    log "WARN: alembic/EXPECTED_HEAD not found, skipping drift check"
fi

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
