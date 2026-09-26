"""Environment-backed configuration helpers for reusable automation infrastructure."""

from __future__ import annotations

import os
from pathlib import Path


class AutomationConfig:
    """Small environment configuration API used by robo-automation internals."""

    @staticmethod
    def get_env_string(name: str, default: str = "") -> str:
        value = os.getenv(name)
        return default if value is None else str(value)

    @staticmethod
    def get_env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None or str(value).strip() == "":
            return bool(default)
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def get_env_int(name: str, default: int = 0) -> int:
        value = os.getenv(name)
        if value is None or str(value).strip() == "":
            return int(default)
        try:
            return int(str(value).strip())
        except ValueError:
            return int(default)

    @staticmethod
    def get_project_root() -> Path:
        """Return the current pytest/application working directory."""
        return Path.cwd()
