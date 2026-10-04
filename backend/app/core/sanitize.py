"""Input sanitization utilities."""

import re
from typing import Optional

import bleach

ALLOWED_TAGS: list[str] = []
ALLOWED_ATTRIBUTES: dict = {}


def sanitize_string(value: Optional[str], max_length: int = 500) -> Optional[str]:
    if value is None:
        return None
    cleaned = bleach.clean(value.strip(), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return cleaned[:max_length] if cleaned else None


def sanitize_email(email: str) -> str:
    return bleach.clean(email.strip().lower(), tags=[], attributes={})


def sanitize_phone(phone: str) -> str:
    return re.sub(r"[^\d+\-\s()]", "", phone.strip())[:20]
