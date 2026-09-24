"""JSON report envelope shared by all commands that save results."""

from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from robzone_diag import __version__

SCHEMA_VERSION = 1


def envelope(command: str, parameters: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "robzone-diag",
        "tool_version": __version__,
        "command": command,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "platform": {"system": platform.system(), "python": platform.python_version()},
        "parameters": parameters,
        "results": results,
    }


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
