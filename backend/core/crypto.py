"""Simple AES encryption for storing user API keys."""
import base64
import json
import os
from cryptography.fernet import Fernet

from core.config import settings


def _get_fernet() -> Fernet:
    key = settings.jwt_secret.encode("utf-8")
    key = key.ljust(32)[:32]
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_keys(keys: dict) -> str:
    return _get_fernet().encrypt(json.dumps(keys).encode()).decode()


def decrypt_keys(encrypted: str | None) -> dict:
    if not encrypted:
        return {}
    try:
        return json.loads(_get_fernet().decrypt(encrypted.encode()))
    except Exception:
        return {}
