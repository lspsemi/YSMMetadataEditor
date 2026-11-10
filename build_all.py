# SPDX-License-Identifier: GPL-3.0-only
"""Rebuild every native/Java component and the Windows GUI bundle."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    for script in ("build_parser.py", "build_encryptor.py", "build_release.py"):
        print(f"\n=== {script} ===", flush=True)
        subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
