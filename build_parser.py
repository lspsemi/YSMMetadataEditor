# SPDX-License-Identifier: GPL-3.0-only
"""Build the vendored YSMParser and copy the executable into bin/."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "native" / "YSMParser"
BUILD = ROOT / ".build" / "YSMParser"
OUTPUT = ROOT / "bin" / "YSMParser.exe"


def main() -> None:
    if os.name != "nt":
        raise RuntimeError("此构建脚本目前仅支持 Windows。")
    if not SOURCE.is_dir() or not (SOURCE / "CMakeLists.txt").is_file():
        raise FileNotFoundError(f"缺少 YSMParser 源码：{SOURCE}")
    cmake = os.environ.get("CMAKE") or shutil.which("cmake")
    if not cmake:
        raise FileNotFoundError("找不到 CMake。可设置 CMAKE 环境变量为 cmake.exe 的完整路径。")
    if not BUILD.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("编译目录必须位于源码仓库内。")
    subprocess.run([cmake, "-S", str(SOURCE), "-B", str(BUILD), "-A", "x64",
                    "-DYSM_TARGET_JNI=OFF"], check=True)
    subprocess.run([cmake, "--build", str(BUILD), "--config", "Release",
                    "--target", "YSMParser"], check=True)
    candidates = (BUILD / "YSMParser" / "Release" / "YSMParser.exe",
                  BUILD / "YSMParser" / "YSMParser.exe")
    executable = next((path for path in candidates if path.is_file()), None)
    if executable is None:
        raise FileNotFoundError(f"编译成功但未找到 YSMParser.exe：{BUILD}")
    OUTPUT.parent.mkdir(exist_ok=True)
    shutil.copy2(executable, OUTPUT)
    print(f"已构建：{OUTPUT}")


if __name__ == "__main__":
    main()
