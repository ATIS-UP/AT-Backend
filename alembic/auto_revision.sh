#!/bin/sh
# Crea una nueva migración de Alembic apuntando automáticamente al head actual.
# Uso: ./alembic/auto_revision.sh "add foo to bar"
set -eu
DESC="${1:?usage: ./alembic/auto_revision.sh \"description\"}"

# Genera la migración con el nombre estándar de Alembic
alembic revision -m "$DESC"

# Encuentra el archivo recién creado (último .py modificado en alembic/versions/)
FNAME=$(ls -t alembic/versions/*.py 2>/dev/null | grep -v __init__ | head -1)
if [ -z "$FNAME" ]; then
    echo "ERROR: no se pudo detectar el archivo de migración recién creado" >&2
    exit 1
fi

# Obtiene el head actual de Alembic (filtra líneas de log tipo INFO/WARNING que
# esta versión de alembic puede emitir a stdout/stderr)
HEAD=$(alembic heads 2>/dev/null | grep "(head)" | head -1 | awk '{print $1}')
if [ -z "$HEAD" ]; then
    echo "ERROR: no se pudo obtener el alembic head actual" >&2
    exit 1
fi

# Sobrescribe down_revision en el archivo recién creado
if grep -q "^down_revision" "$FNAME"; then
    sed -i "s/^down_revision = .*/down_revision = '$HEAD'/" "$FNAME"
else
    echo "WARNING: $FNAME no contiene línea down_revision, revisar manualmente" >&2
fi

# Actualiza el archivo EXPECTED_HEAD con el nuevo head
echo "$HEAD" > alembic/EXPECTED_HEAD

echo "✓ Migración creada: $FNAME"
echo "✓ down_revision = $HEAD (head actual)"
echo "✓ alembic/EXPECTED_HEAD actualizado a $HEAD"
