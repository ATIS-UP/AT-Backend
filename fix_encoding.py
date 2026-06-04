"""Repara datos con doble encoding Latin1→UTF-8 en la base de datos."""
import sys
from app.database import SessionLocal
from app.models.novedad_caso import NovedadCaso
from app.models.caso_especial import RegistroCasoEspecial, HistorialRegistro


def fix_encoding(text):
    """Convierte texto mal codificado Latin1→UTF-8 de vuelta a UTF-8 correcto."""
    if text is None:
        return None, False
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        if fixed != text:
            return fixed, True
        return text, False
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text, False


def main():
    db = SessionLocal()
    fixed_total = 0

    try:
        # 1. Novedades: nombre y descripcion
        novedades = db.query(NovedadCaso).all()
        for n in novedades:
            changed = False
            new_nombre, c1 = fix_encoding(n.nombre)
            if c1:
                n.nombre = new_nombre
                changed = True
            new_desc, c2 = fix_encoding(n.descripcion)
            if c2:
                n.descripcion = new_desc
                changed = True
            if changed:
                fixed_total += 1
        db.flush()

        # 2. Registros: observaciones
        registros = db.query(RegistroCasoEspecial).all()
        for r in registros:
            new_obs, changed = fix_encoding(r.observaciones)
            if changed:
                r.observaciones = new_obs
                fixed_total += 1
        db.flush()

        # 3. Historial: observaciones
        historiales = db.query(HistorialRegistro).all()
        for h in historiales:
            new_obs, changed = fix_encoding(h.observaciones)
            if changed:
                h.observaciones = new_obs
                fixed_total += 1
        db.flush()

        db.commit()
        print(f"Corregidos {fixed_total} registros con encoding roto.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
