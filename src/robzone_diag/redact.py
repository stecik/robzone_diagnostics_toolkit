"""Masking of identifiers before output is shared publicly (issues, PRs, fixtures).

Redaction keeps what matters for diagnosis (vendor OUI, protocol version,
product key) and masks what identifies one household or one physical unit.
Always review a redacted file yourself before publishing it.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Per-device identifiers, user-chosen names and secrets in Tuya announcements and similar
# payloads. Secrets should never appear in a broadcast; they are listed defensively.
DEVICE_ID_KEYS = frozenset(
    {
        "gwId",
        "devId",
        "id",
        "uuid",
        "mac",
        "sn",
        "serial",
        "name",
        "key",
        "localKey",
        "local_key",
        "token",
    }
)


def mac(value: str | None) -> str | None:
    """Keep the vendor prefix (OUI), mask the device-specific half."""
    if not value:
        return value
    return ":".join(value.split(":")[:3] + ["xx", "xx", "xx"])


def identifier(value: Any) -> str:
    """Stable pseudonym so redacted records can still be correlated with each other."""
    digest = hashlib.sha256(str(value).encode()).hexdigest()[:8]
    return f"<redacted:{digest}>"


def hostname(value: str | None) -> str | None:
    return identifier(value) if value else value


def payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: identifier(value) if key in DEVICE_ID_KEYS and value else value
        for key, value in data.items()
    }
