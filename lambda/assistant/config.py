"""Runtime configuration.

Secrets are never committed. They are read, in order, from:

1. Environment variables (own AWS Lambda).
2. ``lambda/config.json`` (Alexa-hosted skills, which do not support env vars).
   This file is git-ignored; see ``config.example.json``.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


@lru_cache(maxsize=1)
def _file_settings() -> dict[str, str]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def get_setting(name: str, default: str | None = None) -> str:
    """Return a setting by its upper-case env name (e.g. ``MOODLE_TOKEN``).

    Raises ``ConfigError`` if it is missing and no ``default`` is given.
    """
    value = os.environ.get(name) or _file_settings().get(name.lower()) or default
    if not value:
        raise ConfigError(f"Missing setting {name!r}: set it as an env var or in config.json.")
    return value
