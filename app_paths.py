# SPDX-License-Identifier: GPL-3.0-only
"""Paths shared by source runs and packaged Windows executables."""

from __future__ import annotations

import os
import sys
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def application_dir() -> Path:
    return Path(sys.executable).resolve().parent if is_frozen() else SOURCE_DIR


def resource_path(*parts: str) -> Path:
    """Prefer files next to the executable, then bundled PyInstaller data."""
    locations = [application_dir()]
    if is_frozen():
        locations.extend((application_dir() / "_internal", Path(getattr(sys, "_MEIPASS", application_dir()))))
    for location in locations:
        candidate = location.joinpath(*parts)
        if candidate.exists():
            return candidate
    return locations[0].joinpath(*parts)


def initial_browse_dir() -> Path:
    documents = Path.home() / "Documents"
    return documents if documents.is_dir() else Path.home()


def settings_file() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".config")
    return base / "YSMMetadataEditor" / "settings.json"
