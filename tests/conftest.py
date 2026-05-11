"""test configuration - sets required environment variables before app imports."""
import os

# set required env vars before any app module is imported
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-minimum-32-characters-long")
os.environ.setdefault("FERNET_KEY", "EOnyi7ibm2_LosSxvwdAfUdVGJcpRKSIP09kKWIrZLM=")
