"""Settings from environment variables and an optional local ``.env`` file.

Secrets (auth codes, device IDs) are read only from here, never from command-line
arguments, so they do not end up in shell history or process listings.
Real environment variables take precedence over ``.env``.
"""

from __future__ import annotations

import os
from pathlib import Path

PREFIX = "ROBZONE_DIAG_"
DEFAULT_ENV_FILE = Path(".env")


class ConfigError(ValueError):
    pass


def parse_env_file(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(env_file: Path | None = DEFAULT_ENV_FILE) -> dict[str, str]:
    settings: dict[str, str] = {}
    if env_file and env_file.is_file():
        settings.update(parse_env_file(env_file.read_text(encoding="utf-8")))
    settings.update({k: v for k, v in os.environ.items() if k.startswith(PREFIX)})
    return {k: v for k, v in settings.items() if k.startswith(PREFIX) and v}


def require(settings: dict[str, str], *names: str) -> list[str]:
    missing = [PREFIX + n for n in names if PREFIX + n not in settings]
    if missing:
        raise ConfigError(
            "missing settings: " + ", ".join(missing) + ". Put them in .env (see .env.example "
            "and README section 'Connecting to the robot')."
        )
    return [settings[PREFIX + n] for n in names]
