"""Seed de usuarios de prueba para MFA"""
from sqlalchemy import text
from app.database import engine
from app.utils.security import hash_password


USUARIOS = [
    ("ogaitanc09@gmail.com", "gaitan123", "Oscar Gaitan", "DOCENTE"),
    ("djulian090104@gmail.com", "julian123", "Didier Tabaco", "DOCENTE"),
]


def seed_mfa_usuarios():
    with engine.connect() as conn:
        print("Creando usuarios de prueba MFA...")
        for email, password, nombre, rol in USUARIOS:
            password_hash = hash_password(password)
            conn.execute(text("""
                INSERT INTO users (id, email, password_hash, nombre, rol, is_active, is_verified)
                SELECT gen_random_uuid(), :email, :password_hash, :nombre, CAST(:rol AS rolenum), true, true
                WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = :email)
            """), {"email": email, "password_hash": password_hash, "nombre": nombre, "rol": rol})
            print(f"  - {email} ({rol})")
        conn.commit()
        print("Usuarios MFA creados/verificados.")


if __name__ == "__main__":
    seed_mfa_usuarios()
