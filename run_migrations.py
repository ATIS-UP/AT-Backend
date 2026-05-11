"""apply alembic migrations to create all tables"""
import sys
import os

sys.path.insert(0, '/home/fabian/Documents/university/TrabajoSocial/AT-Backend')
os.chdir('/home/fabian/Documents/university/TrabajoSocial/AT-Backend')

from alembic.config import Config
from alembic import command

alembic_cfg = Config('/home/fabian/Documents/university/TrabajoSocial/AT-Backend/alembic.ini')
alembic_cfg.set_main_option('script_location', '/home/fabian/Documents/university/TrabajoSocial/AT-Backend/alembic')

try:
    command.upgrade(alembic_cfg, 'head')
    print("Migrations applied successfully!")
except Exception as e:
    print(f"Migration failed: {e}")
    # fallback: create tables directly
    print("Falling back to direct table creation...")
    from app.database import engine, Base
    import app.models  # noqa: ensure all models are imported
    Base.metadata.create_all(bind=engine)
    print("Tables created directly via SQLAlchemy.")
