import logging
import re
from collections.abc import Mapping
from typing import Any

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = frozenset(
    {"authorization", "api_key", "apikey", "password", "private_key", "token", "secret"}
)
_SECRET_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}", re.IGNORECASE),
    re.compile(r"\bsk-(?:proj-|ant-api\d*-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bpassword\s*[:=]\s*[^\s'\"]{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*", re.DOTALL),
)


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _REDACTED if str(key).lower() in _SENSITIVE_KEYS else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        for pattern in _SECRET_PATTERNS:
            value = pattern.sub(_REDACTED, value)
    return value


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_value(record.msg)
        record.args = redact_value(record.args)
        return True
