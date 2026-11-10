# SPDX-License-Identifier: GPL-3.0-only
"""Small per-user preferences for the editor."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from app_paths import settings_file


def last_model_directory() -> Path | None:
    try:
        data = json.loads(settings_file().read_text(encoding="utf-8"))
        candidate = data.get("last_model_directory")
        if isinstance(candidate, str):
            path = Path(candidate)
            if path.is_dir():
                return path
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def remember_model_directory(directory: Path) -> None:
    path = settings_file()
    temporary: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=".settings-",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = stream.name
            json.dump({"last_model_directory": str(directory.resolve())}, stream, ensure_ascii=False)
        os.replace(temporary, path)
    except OSError:
        # A read-only profile should not prevent browsing or editing models.
        pass
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                pass
