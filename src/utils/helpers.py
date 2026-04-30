"""General-purpose helper functions."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def env(key: str, default: str | None = None) -> str:
        """Read an environment variable or return *default*."""
        value = os.getenv(key, default)
        if value is None:
                    raise OSError(f"Missing required env var: {key}")
                return value


def project_root() -> Path:
        """Return the absolute path to the repository root."""
    return Path(__file__).resolve().parents[2]


def sha256_digest(data: bytes) -> str:
        """Return the hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()
