"""Environment variable loader for OpenMontage.

Loads .env file and provides typed access to environment configuration.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from lib.workspace_config import configure_process_environment


def load_env(project_root: Optional[Path] = None) -> None:
    """Load the shared workspace env and compatibility aliases."""
    configure_process_environment(project_root or Path(__file__).resolve().parent.parent)


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get an environment variable with optional default."""
    return os.environ.get(key, default)


def require_env(key: str) -> str:
    """Get a required environment variable. Raises if missing."""
    value = os.environ.get(key)
    if value is None:
        raise EnvironmentError(f"Required environment variable {key!r} is not set")
    return value
