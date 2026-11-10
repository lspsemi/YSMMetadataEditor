# SPDX-License-Identifier: GPL-3.0-only
"""Build a Windows GUI bundle with a console batch-encryption helper."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "Release"
NAME = "YSMMetadataEditor"


def run_pyinstaller(*options: str) -> None:
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", *options],
                   cwd=ROOT, check=True)


def main() -> int:
    if os.name != "nt":
        raise RuntimeError("发布构建脚本目前仅支持 Windows。")
    if not (ROOT / "bin" / "YSMParser.exe").is_file():
        raise FileNotFoundError("缺少 bin/YSMParser.exe")
    if not (ROOT / "bin" / "encryptor" / "ysm-encryptor.jar").is_file():
        raise FileNotFoundError("缺少 bin/encryptor/ysm-encryptor.jar")
    if not RELEASE.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("发布目录必须位于项目目录内。")
    RELEASE.mkdir(exist_ok=True)
    helper_stage = RELEASE / "helper"
    spec_dir = RELEASE / "spec"
    run_pyinstaller(
        "--onefile", "--console", "--name", "BatchEncrypt",
        "--distpath", str(helper_stage),
        "--workpath", str(RELEASE / "build-helper"),
        "--specpath", str(spec_dir),
        str(ROOT / "batch_encrypt.py"),
    )
    run_pyinstaller(
        "--onedir", "--windowed", "--contents-directory", ".",
        "--name", NAME,
        "--add-binary", f"{ROOT / 'bin' / 'YSMParser.exe'}{os.pathsep}bin",
        "--add-data", f"{ROOT / 'bin' / 'encryptor'}{os.pathsep}bin/encryptor",
        "--distpath", str(RELEASE),
        "--workpath", str(RELEASE / "build-gui"),
        "--specpath", str(spec_dir),
        str(ROOT / "ysm_metadata_editor.py"),
    )
    target = RELEASE / NAME / "BatchEncrypt.exe"
    shutil.copy2(helper_stage / "BatchEncrypt.exe", target)
    shutil.copytree(ROOT / "third_party" / "licenses", RELEASE / NAME / "licenses",
                    dirs_exist_ok=True)
    print(f"发布目录：{target.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
