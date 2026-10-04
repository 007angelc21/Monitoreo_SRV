"""Genera FERNET_KEY: python scripts/gen-fernet.py"""
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
