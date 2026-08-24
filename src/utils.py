"""Utilities for locating project paths."""

from pathlib import Path


def get_project_root() -> Path:
    """Return the project root directory (one level above src/)."""
    return Path(__file__).resolve().parents[1]