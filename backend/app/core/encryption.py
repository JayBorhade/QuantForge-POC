"""Fernet encryption for sensitive credentials at rest."""

import base64
import hashlib
import json
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _get_fernet() -> Fernet:
    settings = get_settings()
    key_material = settings.effective_encryption_key.encode()
    digest = hashlib.sha256(key_material).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def encrypt_credentials(
    api_key: str,
    api_secret: str,
    access_token: Optional[str] = None,
) -> str:
    payload = {
        "api_key": api_key,
        "api_secret": api_secret,
        "access_token": access_token,
    }
    return encrypt_value(json.dumps(payload))


def decrypt_credentials(encrypted: str) -> Dict[str, Any]:
    data = json.loads(decrypt_value(encrypted))
    return {
        "api_key": data.get("api_key", ""),
        "api_secret": data.get("api_secret", ""),
        "access_token": data.get("access_token"),
    }


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 12:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"
