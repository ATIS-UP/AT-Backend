"""Seed2: Rename old MFA test users and recreate with fresh accounts"""
from sqlalchemy import text
from app.database import engine
from app.utils.security import hash_password

USUARIOS_VIEJOS = [
    ("ogaitanc09@gmail.com", "ogaitanc09.old1@gmail.com"),
    ("djulian090104@gmail.com", "djulian090104.old1@gmail.com"),
]

USUARIOS_NUEVOS = [
    ("ogaitanc09@gmail.com", "gaitan123", "Oscar Gaitan", "DOCENTE"),
    ("djulian090104@gmail.com", "julian123", "Didier Tabaco", "DOCENTE"),
]


def renovar_mfa_usuarios():
    with engine.connect() as conn:
        # 1. Renombrar usuarios existentes (mover a email .old)
        for old_email, new_email in USUARIOS_VIEJOS:
            result = conn.execute(
                text("UPDATE users SET email = :new_email WHERE email = :old_email"),
                {"old_email": old_email, "new_email": new_email},
            )
            if result.rowcount > 0:
                print(f"  Renombrado {old_email} -> {new_email}")

        # 2. Crear nuevos usuarios frescos (mfa_enabled=False por defecto)
        for email, password, nombre, rol in USUARIOS_NUEVOS:
            password_hash = hash_password(password)
            conn.execute(text("""
                INSERT INTO users (id, email, password_hash, nombre, rol, is_active, is_verified)
                VALUES (gen_random_uuid(), :email, :password_hash, :nombre, CAST(:rol AS rolenum), true, true)
                ON CONFLICT (email) DO NOTHING
            """), {"email": email, "password_hash": password_hash, "nombre": nombre, "rol": rol})
            print(f"  Creado {email} ({rol})")

        conn.commit()
        print("Usuarios MFA renovados.")


if __name__ == "__main__":
    renovar_mfa_usuarios()
