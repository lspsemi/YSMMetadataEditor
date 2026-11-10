# SPDX-License-Identifier: GPL-3.0-only
"""Build the OpenYSM folder encryptor from the vendored source snapshot."""

from __future__ import annotations

import os
import json
import hashlib
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "third_party" / "openysm-src"
LIBRARIES = ROOT / "third_party" / "java-libs"
OUTPUT = ROOT / "bin" / "encryptor"
JARS = (
    "gson-2.10.1.jar",
    "joml-1.10.5.jar",
    "netty-buffer-4.1.110.Final.jar",
    "netty-common-4.1.110.Final.jar",
)

SOURCE_FILES = [
    "com/elfmcys/yesstevemodel/resource/YSMFolderDeserializer.java",
    "com/elfmcys/yesstevemodel/resource/YSMBinarySerializer.java",
    "com/elfmcys/yesstevemodel/resource/pojo/RawYsmModel.java",
    "com/elfmcys/yesstevemodel/util/DigestUtil.java",
    "rip/ysm/security/YSMByteBuf.java",
    "rip/ysm/security/YsmCrypt.java",
    "rip/ysm/algorithms/CityHash.java",
    "rip/ysm/algorithms/MT19937.java",
    "rip/ysm/algorithms/XChaCha20.java",
    "rip/ysm/algorithms/ChaCha20Base.java",
    "rip/ysm/algorithms/YsmZstd.java",
]


def jdk_tool(name: str) -> str:
    exe = name + (".exe" if os.name == "nt" else "")
    home = Path(os.environ.get("JAVA_HOME", ""))
    if (home / "bin" / exe).is_file():
        return str(home / "bin" / exe)
    found = shutil.which(exe)
    if found:
        return found
    java = shutil.which("java")
    if java:
        result = subprocess.run([java, "-XshowSettings:properties", "-version"],
                                capture_output=True, text=True, errors="replace")
        match = re.search(r"^\s*java\.home\s*=\s*(.+)$", result.stderr, re.MULTILINE)
        if match:
            candidate = Path(match.group(1).strip()) / "bin" / exe
            if candidate.is_file():
                return str(candidate)
    raise FileNotFoundError(f"找不到 {exe}，请安装 JDK 17 或更高版本。")


def main() -> None:
    if not SOURCE.is_dir():
        raise FileNotFoundError(f"找不到本仓库的 OpenYSM 源码：{SOURCE}")
    jars = [LIBRARIES / name for name in JARS]
    missing = [path.name for path in jars if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"缺少 Java 依赖：{', '.join(missing)}")
    expected = json.loads((LIBRARIES / "SHA256SUMS.json").read_text(encoding="utf-8"))
    for jar in jars:
        actual = hashlib.sha256(jar.read_bytes()).hexdigest()
        if actual != expected.get(jar.name):
            raise ValueError(f"依赖文件校验失败：{jar.name}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for jar in jars:
        shutil.copy2(jar, OUTPUT / jar.name)
    classes = OUTPUT / "classes"
    if classes.exists():
        if not classes.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError("编译目录不在源码仓库内。")
        shutil.rmtree(classes)
    classes.mkdir(parents=True, exist_ok=True)
    sources = [SOURCE / name for name in SOURCE_FILES]
    sources += sorted((SOURCE / "rip" / "ysm" / "zstd").glob("*.java"))
    sources += sorted((ROOT / "java").rglob("*.java"))
    command = [jdk_tool("javac"), "-encoding", "UTF-8", "-source", "17", "-target", "17",
               "-cp", os.pathsep.join(map(str, jars)), "-d", str(classes), *map(str, sources)]
    subprocess.run(command, check=True)
    subprocess.run([jdk_tool("jar"), "--create", "--file", str(OUTPUT / "ysm-encryptor.jar"),
                    "-C", str(classes), "."], check=True)
    print(f"已构建：{OUTPUT / 'ysm-encryptor.jar'}")


if __name__ == "__main__":
    main()
