from cryptography.fernet import Fernet

from api.config import get_settings


def encrypt_pat(pat: str) -> str:
    f = Fernet(get_settings().pat_encryption_key.encode())
    return f.encrypt(pat.encode()).decode()


def decrypt_pat(encrypted: str) -> str:
    f = Fernet(get_settings().pat_encryption_key.encode())
    return f.decrypt(encrypted.encode()).decode()
