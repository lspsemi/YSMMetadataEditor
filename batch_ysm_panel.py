# SPDX-License-Identifier: GPL-3.0-only
"""Batch YSM conversion panel backed by the local parser and OpenYSM helper."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from app_paths import application_dir, initial_browse_dir, is_frozen, resource_path


PARSER_EXE = resource_path("bin", "YSMParser.exe")
ENCRYPTOR_DIR = resource_path("bin", "encryptor")


def conversion_command(mode: str, input_dir: Path, output_dir: Path,
                       reverse_render: bool = True, threads: int = 0) -> list[str]:
    if mode == "decrypt":
        if not PARSER_EXE.is_file():
            raise FileNotFoundError(f"找不到 YSMParser：{PARSER_EXE}")
        command = [str(PARSER_EXE), "-i", str(input_dir), "-o", str(output_dir),
                   "--threads", str(threads)]
        if not reverse_render:
            command.append("--no-reverse-render")
        return command
    if mode == "encrypt":
        if not (ENCRYPTOR_DIR / "ysm-encryptor.jar").is_file():
            raise FileNotFoundError("找不到 OpenYSM 加密组件，请先构建加密组件。")
        if is_frozen():
            helper = application_dir() / "BatchEncrypt.exe"
            if not helper.is_file():
                raise FileNotFoundError(f"找不到批量加密辅助程序：{helper}")
            return [str(helper), str(input_dir), str(output_dir)]
        return [sys.executable, "-X", "utf8", "-u", str(resource_path("batch_encrypt.py")),
                str(input_dir), str(output_dir)]
    raise ValueError(f"未知操作：{mode}")


class BatchPanel(ttk.Frame):
    def __init__(self, parent: tk.Misc, initial_dir: Path | None = None) -> None:
        super().__init__(parent, padding=14)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(7, weight=1)
        self.mode = tk.StringVar(value="decrypt")
        self.input_dir = tk.StringVar(value=str(initial_dir) if initial_dir else "")
        self.output_dir = tk.StringVar(value="")
        self.reverse_render = tk.BooleanVar(value=True)
        self.threads = tk.StringVar(value="0")
        self.events: queue.Queue[tuple[str, str | int]] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.worker: threading.Thread | None = None
        self._closing = threading.Event()

        ttk.Label(self, text="YSM 模型批量加解密", font=("Microsoft YaHei UI", 13, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )
        mode_frame = ttk.Frame(self)
        mode_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="批量解密 .ysm", value="decrypt", variable=self.mode,
                        command=self._mode_changed).pack(side="left")
        ttk.Radiobutton(mode_frame, text="批量加密模型文件夹", value="encrypt", variable=self.mode,
                        command=self._mode_changed).pack(side="left", padx=16)

        ttk.Label(self, text="输入目录").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(self, textvariable=self.input_dir).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(self, text="浏览", command=lambda: self._choose_directory(self.input_dir)).grid(row=2, column=2)
        ttk.Label(self, text="输出目录").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(self, textvariable=self.output_dir).grid(row=3, column=1, sticky="ew", padx=8)
        ttk.Button(self, text="浏览", command=lambda: self._choose_directory(self.output_dir)).grid(row=3, column=2)

        options = ttk.Frame(self)
        options.grid(row=4, column=0, columnspan=3, sticky="w", pady=8)
        self.reverse_check = ttk.Checkbutton(options, text="解密时应用反渲染（还原 Blockbench 立方体）",
                                             variable=self.reverse_render)
        self.reverse_check.pack(side="left")
        ttk.Label(options, text="线程数（0=自动）").pack(side="left", padx=(18, 4))
        self.thread_entry = ttk.Entry(options, width=5, textvariable=self.threads)
        self.thread_entry.pack(side="left")

        self.hint = ttk.Label(self, text="", wraplength=760)
        self.hint.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))
        actions = ttk.Frame(self)
        actions.grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.start_button = ttk.Button(actions, text="开始处理", command=self.start)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(actions, text="取消", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.log = tk.Text(self, wrap="word", state="disabled")
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew")
        self._mode_changed()

    def _mode_changed(self) -> None:
        decrypt = self.mode.get() == "decrypt"
        self.reverse_check.configure(state="normal" if decrypt else "disabled")
        self.thread_entry.configure(state="normal" if decrypt else "disabled")
        if decrypt:
            self.hint.configure(text="递归处理输入目录中的 .ysm 文件。关闭反渲染后输出原始面顶点、法线和 UV；这类模型 JSON 不能直接作为 Blockbench 立方体编辑。")
        else:
            self.hint.configure(text="递归处理包含 ysm.json 的解密模型目录，输出同名 .ysm 文件。")

    def _choose_directory(self, variable: tk.StringVar) -> None:
        initial = Path(variable.get()) if variable.get().strip() else initial_browse_dir()
        chosen = filedialog.askdirectory(initialdir=initial if initial.is_dir() else initial_browse_dir())
        if chosen:
            variable.set(chosen)

    def use_model_directory(self, directory: Path, previous: Path | None = None) -> None:
        if not self.input_dir.get().strip() or (previous is not None and self.input_dir.get() == str(previous)):
            self.input_dir.set(str(directory))

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.input_dir.get().strip():
            messagebox.showerror("输入目录错误", "请选择输入目录。", parent=self)
            return
        input_dir = Path(self.input_dir.get().strip())
        output_dir = Path(self.output_dir.get().strip())
        if not input_dir.is_dir():
            messagebox.showerror("输入目录错误", f"目录不存在：{input_dir}", parent=self)
            return
        if not str(self.output_dir.get()).strip() or input_dir.resolve() == output_dir.resolve():
            messagebox.showerror("输出目录错误", "输出目录不能留空或与输入目录相同。", parent=self)
            return
        try:
            threads = int(self.threads.get()) if self.mode.get() == "decrypt" else 0
            if threads < 0:
                raise ValueError("线程数不能小于 0")
            command = conversion_command(self.mode.get(), input_dir, output_dir,
                                         self.reverse_render.get(), threads)
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("无法启动", str(exc), parent=self)
            return
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._append_log(f"输入：{input_dir}\n输出：{output_dir}\n开始处理...\n\n")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.worker = threading.Thread(target=self._run, args=(command,), daemon=True)
        self.worker.start()
        self.after(100, self._poll_events)

    def _run(self, command: list[str]) -> None:
        try:
            self.process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if self._closing.is_set():
                self._terminate_process()
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.events.put(("log", line))
            code = self.process.wait()
            self.events.put(("done", code))
        except OSError as exc:
            self.events.put(("log", f"启动失败：{exc}\n"))
            self.events.put(("done", -1))

    def _poll_events(self) -> None:
        finished = None
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(str(value))
                elif kind == "done":
                    finished = int(value)
        except queue.Empty:
            pass
        if finished is None:
            self.after(100, self._poll_events)
            return
        self.process = None
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self._append_log(f"\n处理结束，退出码：{finished}\n")

    def cancel(self) -> None:
        if self.process and self.process.poll() is None:
            self._terminate_process()
            self._append_log("正在取消...\n")

    def _terminate_process(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        else:
            process.terminate()

    def shutdown(self) -> None:
        self._closing.set()
        self._terminate_process()
