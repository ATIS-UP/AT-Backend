"""backfill documento_hash for estudiantes

Revision ID: 3de7e1d1cf0c
Revises: add_email_hash_to_estudiantes
Create Date: 2026-06-13 16:06:41.078997+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.utils.security import decrypt_data, hash_data


# revision identifiers, used by Alembic.
revision: str = '3de7e1d1cf0c'
down_revision: Union[str, None] = 'add_email_hash_to_estudiantes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BATCH_SIZE = 200


def upgrade() -> None:
    """Populate documento_hash for students whose documento_hash is NULL.

    documento_hash was added by a previous migration without a backfill, so
    students created/imported before that migration (or via carga masiva
    before it computed documento_hash) cannot be found by the public survey
    verification endpoint, which looks up Estudiante.documento_hash. This is
    a one-time data fix; safe to re-run (idempotent) since it only touches
    rows where documento_hash IS NULL.
    """
    bind = op.get_bind()

    while True:
        rows = bind.execute(
            sa.text(
                "SELECT id, documento FROM estudiantes "
                "WHERE documento_hash IS NULL AND documento IS NOT NULL "
                "LIMIT :limit"
            ),
            {"limit": BATCH_SIZE},
        ).fetchall()

        if not rows:
            break

        for row in rows:
            try:
                documento = decrypt_data(row.documento)
            except Exception:
                documento = "[DATO_CORRUPTO]"

            if not documento or documento == "[DATO_CORRUPTO]":
                # cannot decrypt; leave documento_hash NULL for this row
                continue

            documento_hash = hash_data(documento.strip())

            # documento_hash is unique; skip rows whose hash collides with
            # an already-populated value (duplicate/legacy documento).
            dup = bind.execute(
                sa.text("SELECT 1 FROM estudiantes WHERE documento_hash = :h"),
                {"h": documento_hash},
            ).first()
            if dup:
                continue

            bind.execute(
                sa.text("UPDATE estudiantes SET documento_hash = :h WHERE id = :id"),
                {"h": documento_hash, "id": row.id},
            )


def downgrade() -> None:
    # Not reversible with precision: clearing documento_hash for backfilled
    # rows would also undo data populated by normal app usage after this
    # migration ran. Intentionally a no-op.
    pass
