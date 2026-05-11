"""test database connection"""
import sys
sys.path.insert(0, '/home/fabian/Documents/university/TrabajoSocial/AT-Backend')

import os
os.chdir('/home/fabian/Documents/university/TrabajoSocial/AT-Backend')

from app.database import engine

try:
    conn = engine.connect()
    print("DB connection OK")
    conn.close()
except Exception as e:
    print(f"DB connection FAILED: {e}")
