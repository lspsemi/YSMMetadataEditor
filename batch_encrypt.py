# SPDX-License-Identifier: GPL-3.0-only
"""Encrypt decrypted YSM model folders using the OpenYSM serializer."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from app_paths import resource_path

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None


ENCRYPTOR = resource_path("bin", "encryptor")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".bmp", ".tif", ".tiff"}
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def prepare_model(source: Path, staging: Path) -> None:
    shutil.copytree(source, staging, ignore=shutil.ignore_patterns("ysm.json.*.bak"))
    for path in staging.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        with path.open("rb") as stream:
            if stream.read(8) == PNG_MAGIC:
                continue
        if Image is None or ImageOps is None:
            raise RuntimeError(f"需要 Pillow 转换图片：{path.relative_to(staging)}。请运行 python -m pip install pillow")
        with Image.open(path) as image:
            converted = ImageOps.exif_transpose(image).convert("RGBA")
            converted.save(path, format="PNG")


def model_targets(input_root: Path, output_root: Path) -> list[tuple[Path, Path]]:
    folders = sorted((path.parent for path in input_root.rglob("ysm.json")), key=lambda path: str(path).casefold())
    result = []
    for folder in folders:
        relative = folder.relative_to(input_root)
        if relative == Path("."):
            target = output_root / f"{folder.name}.ysm"
        else:
            target = output_root / relative.parent / f"{relative.name}.ysm"
        result.append((folder, target))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch encrypt decrypted YSM folders")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if not args.input.is_dir():
        parser.error(f"输入目录不存在：{args.input}")
    if not (ENCRYPTOR / "ysm-encryptor.jar").is_file():
        parser.error("缺少 OpenYSM 加密组件")
    targets = model_targets(args.input, args.output)
    print(f"找到 {len(targets)} 个模型文件夹", flush=True)
    if not targets:
        return 0
    success = failed = skipped = 0
    for index, (folder, target) in enumerate(targets, 1):
        print(f"[{index}/{len(targets)}] {folder.name}", flush=True)
        if target.exists():
            print(f"  跳过：目标已存在 {target}", flush=True)
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        pending = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            with tempfile.TemporaryDirectory(prefix="ysm-stage-") as temporary:
                staged = Path(temporary) / folder.name
                prepare_model(folder, staged)
                command = ["java", "-Dfile.encoding=UTF-8", "-cp", str(ENCRYPTOR / "*"),
                           "BatchEncryptor", str(staged), str(pending)]
                process = subprocess.run(command, capture_output=True, text=True,
                                         encoding="utf-8", errors="replace")
                if process.returncode:
                    raise RuntimeError(process.stderr.strip() or process.stdout.strip() or
                                       f"Java 退出码 {process.returncode}")
                os.replace(pending, target)
                print(f"  完成：{target}", flush=True)
                success += 1
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"  失败：{exc}", file=sys.stderr, flush=True)
            failed += 1
        finally:
            if pending.exists():
                pending.unlink()
    print(f"汇总：成功 {success}，失败 {failed}，跳过 {skipped}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
