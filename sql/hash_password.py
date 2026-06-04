"""Generate a bcrypt hash for a given password"""
import sys
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hash_password.py <password>")
        sys.exit(1)
    print(pwd.hash(sys.argv[1]))
