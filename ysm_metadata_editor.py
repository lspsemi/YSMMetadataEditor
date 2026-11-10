# SPDX-License-Identifier: GPL-3.0-only
"""A small editor for decrypted YSM model metadata."""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from app_paths import initial_browse_dir
from app_settings import last_model_directory, remember_model_directory
from batch_ysm_panel import BatchPanel

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:
    Image = None
    ImageOps = None
    ImageTk = None


def read_model(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("ysm.json 的顶层必须是 JSON 对象。")
    if "metadata" in data and not isinstance(data["metadata"], dict):
        raise ValueError("metadata 必须是 JSON 对象。")
    return data


def replace_metadata(model: dict, metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        raise ValueError("metadata 必须是 JSON 对象。")
    result = copy.deepcopy(model)
    result["metadata"] = copy.deepcopy(metadata)
    return result


def save_model(path: Path, data: dict, create_backup: bool = True) -> Path | None:
    """Validate, optionally back up the original, then replace it atomically."""
    if not isinstance(data, dict) or not isinstance(data.get("metadata"), dict):
        raise ValueError("模型必须包含 JSON 对象格式的 metadata。")
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    backup = (
        path.with_name(f"{path.name}.{datetime.now():%Y%m%d-%H%M%S-%f}.bak")
        if create_backup else None
    )
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=".ysm-", suffix=".tmp", delete=False
        ) as stream:
            temp_name = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if backup is not None:
            shutil.copy2(path, backup)
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return backup


class Editor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YSM 模型元数据编辑器")
        self.geometry("1000x720")
        self.minsize(760, 560)
        self.current_path: Path | None = None
        self.model: dict | None = None
        self.working_metadata: dict = {}
        self.active_tab = 0
        self.switching = False
        self.raw_dirty = False
        self.authors_data: list[dict] = []
        self.author_index: int | None = None
        self.contact_data: list[tuple[str, str]] = []
        self.contact_index: int | None = None
        self.pending_avatars: dict[str, Path] = {}
        self.avatar_image = None

        self.remembered_dir = last_model_directory()
        self.root_dir = self.remembered_dir or initial_browse_dir()
        self._build_ui()
        if self.remembered_dir is not None:
            self.refresh_models()
        else:
            self.model_paths = []
            self.root_label.config(text="尚未选择模型目录")
            self.status.config(text="请选择解密模型目录或打开 ysm.json")

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="选择模型目录", command=self.choose_root).pack(side="left")
        ttk.Button(toolbar, text="打开 ysm.json", command=self.choose_file).pack(side="left", padx=5)
        ttk.Button(toolbar, text="保存 Ctrl+S", command=self.save).pack(side="right")
        self.no_backup = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            toolbar, text="不生成 .bak 文件", variable=self.no_backup
        ).pack(side="right", padx=(0, 10))
        self.root_label = ttk.Label(toolbar, text=str(self.root_dir))
        self.root_label.pack(side="left", padx=12)

        self.main_tabs = ttk.Notebook(self)
        self.main_tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        metadata_page = ttk.Frame(self.main_tabs)
        self.main_tabs.add(metadata_page, text="元数据编辑")
        self.batch_panel = BatchPanel(self.main_tabs, initial_dir=self.remembered_dir)
        self.main_tabs.add(self.batch_panel, text="批量加解密")
        pane = ttk.PanedWindow(metadata_page, orient="horizontal")
        pane.pack(fill="both", expand=True)
        sidebar = ttk.Frame(pane)
        pane.add(sidebar, weight=1)
        ttk.Label(sidebar, text="解密模型（双击打开）").pack(anchor="w", pady=(0, 5))
        self.model_list = tk.Listbox(sidebar, exportselection=False)
        self.model_list.pack(fill="both", expand=True)
        self.model_list.bind("<Double-Button-1>", self.open_selected)
        ttk.Button(sidebar, text="刷新列表", command=self.refresh_models).pack(fill="x", pady=(5, 0))

        right = ttk.Frame(pane)
        pane.add(right, weight=3)
        self.file_label = ttk.Label(right, text="请选择一个解密模型的 ysm.json")
        self.file_label.pack(anchor="w", pady=(0, 5))
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self.basic = ttk.Frame(self.tabs, padding=12)
        self.advanced = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.basic, text="基础信息")
        self.tabs.add(self.advanced, text="高级 metadata JSON")
        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self._build_basic()
        self._build_advanced()
        self.bind_all("<Control-s>", self.save)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.status = ttk.Label(self, text="就绪", padding=(8, 0, 8, 8))
        self.status.pack(fill="x")

    def _build_basic(self) -> None:
        self.basic.columnconfigure(1, weight=1)
        self.basic.rowconfigure(7, weight=1)
        self.vars: dict[str, tk.StringVar] = {}
        fields = [
            ("name", "模型名称"),
            ("license_type", "授权类型"),
            ("license_desc", "授权说明"),
            ("home", "主页链接"),
            ("donate", "赞助链接"),
        ]
        for row, (key, title) in enumerate(fields):
            ttk.Label(self.basic, text=title).grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar()
            self.vars[key] = var
            ttk.Entry(self.basic, textvariable=var).grid(
                row=row, column=1, sticky="ew", padx=(12, 0), pady=4
            )
        ttk.Label(self.basic, text="提示 / 介绍").grid(row=5, column=0, sticky="nw", pady=5)
        self.tips = tk.Text(self.basic, height=5, wrap="word", undo=True)
        self.tips.grid(row=5, column=1, sticky="nsew", padx=(12, 0), pady=4)
        ttk.Label(self.basic, text="作者").grid(row=6, column=0, sticky="nw", pady=5)
        author_panel = ttk.Frame(self.basic)
        author_panel.grid(row=6, column=1, rowspan=2, sticky="nsew", padx=(12, 0), pady=4)
        author_panel.columnconfigure(1, weight=1)
        author_panel.rowconfigure(0, weight=1)
        author_left = ttk.Frame(author_panel)
        author_left.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.author_list = tk.Listbox(author_left, width=18, height=14, exportselection=False)
        self.author_list.pack(fill="both", expand=True)
        self.author_list.bind("<<ListboxSelect>>", self.on_author_selected)
        author_actions = ttk.Frame(author_left)
        author_actions.pack(fill="x", pady=(4, 0))
        ttk.Button(author_actions, text="添加", command=self.add_author).pack(side="left")
        ttk.Button(author_actions, text="删除", command=self.remove_author).pack(side="left", padx=4)

        author_right = ttk.Frame(author_panel)
        author_right.grid(row=0, column=1, sticky="nsew")
        author_right.columnconfigure(1, weight=1)
        self.author_vars = {key: tk.StringVar() for key in ("name", "role", "avatar")}
        for row, (key, label) in enumerate((("name", "姓名"), ("role", "职责"))):
            ttk.Label(author_right, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(author_right, textvariable=self.author_vars[key]).grid(
                row=row, column=1, columnspan=2, sticky="ew", pady=2
            )
        ttk.Label(author_right, text="简介").grid(row=2, column=0, sticky="nw", pady=2)
        self.author_comment = tk.Text(author_right, height=2, wrap="word")
        self.author_comment.grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)
        ttk.Label(author_right, text="头像路径").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(author_right, textvariable=self.author_vars["avatar"]).grid(
            row=3, column=1, sticky="ew", pady=2
        )
        ttk.Button(author_right, text="选择头像", command=self.choose_avatar).grid(
            row=3, column=2, padx=(5, 0)
        )
        self.avatar_preview = ttk.Label(author_right, text="暂无头像")
        self.avatar_preview.grid(row=4, column=1, columnspan=2, sticky="w", pady=2)
        ttk.Button(author_right, text="预览路径", command=self.preview_avatar).grid(
            row=4, column=0, sticky="w"
        )
        ttk.Label(author_right, text="联系方式 / 链接").grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 2))
        self.contact_list = tk.Listbox(author_right, height=4, exportselection=False)
        self.contact_list.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.contact_list.bind("<<ListboxSelect>>", self.on_contact_selected)
        self.contact_key = tk.StringVar()
        self.contact_value = tk.StringVar()
        ttk.Label(author_right, text="平台").grid(row=7, column=0, sticky="w")
        ttk.Entry(author_right, textvariable=self.contact_key).grid(row=7, column=1, columnspan=2, sticky="ew")
        ttk.Label(author_right, text="链接").grid(row=8, column=0, sticky="w")
        ttk.Entry(author_right, textvariable=self.contact_value).grid(row=8, column=1, columnspan=2, sticky="ew")
        contact_actions = ttk.Frame(author_right)
        contact_actions.grid(row=9, column=1, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Button(contact_actions, text="添加链接", command=self.add_contact).pack(side="left")
        ttk.Button(contact_actions, text="删除链接", command=self.remove_contact).pack(side="left", padx=5)
        ttk.Label(
            self.basic,
            text="保存时只替换 metadata，其他模型配置会保留；默认生成 .bak 备份。",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_advanced(self) -> None:
        self.advanced.columnconfigure(0, weight=1)
        self.advanced.rowconfigure(1, weight=1)
        ttk.Label(
            self.advanced,
            text="编辑完整 metadata 对象。切换回基础信息或保存时会检查 JSON。",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.raw = tk.Text(self.advanced, wrap="none", undo=True)
        self.raw.grid(row=1, column=0, sticky="nsew")
        self.raw.bind("<<Modified>>", self._raw_modified)

    def _raw_modified(self, _event=None) -> None:
        if self.raw.edit_modified():
            self.raw_dirty = True
            self.raw.edit_modified(False)

    def refresh_models(self) -> None:
        self.model_paths = sorted(
            self.root_dir.rglob("ysm.json"), key=lambda p: str(p).casefold()
        )
        self.model_list.delete(0, "end")
        for path in self.model_paths:
            self.model_list.insert("end", str(path.parent.relative_to(self.root_dir)))
        self.root_label.config(text=str(self.root_dir))
        self.status.config(text=f"找到 {len(self.model_paths)} 个解密模型")

    def choose_root(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.root_dir, title="选择解密模型目录")
        if chosen:
            previous_root = self.root_dir
            self.root_dir = Path(chosen)
            remember_model_directory(self.root_dir)
            self.batch_panel.use_model_directory(self.root_dir, previous_root)
            self.refresh_models()

    def choose_file(self) -> None:
        chosen = filedialog.askopenfilename(
            initialdir=self.root_dir, title="打开 ysm.json",
            filetypes=[("YSM 元数据", "ysm.json"), ("JSON 文件", "*.json")],
        )
        if chosen:
            self.open_file(Path(chosen))

    def open_selected(self, _event=None) -> None:
        selected = self.model_list.curselection()
        if selected:
            self.open_file(self.model_paths[selected[0]])

    def _text(self, widget: tk.Text) -> str:
        return widget.get("1.0", "end-1c")

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.edit_modified(False)

    def save_current_contact(self) -> None:
        if self.contact_index is None:
            return
        key = self.contact_key.get().strip()
        if not key:
            raise ValueError("联系方式的平台名称不能为空。")
        if any(key == existing and index != self.contact_index
               for index, (existing, _) in enumerate(self.contact_data)):
            raise ValueError(f"联系方式的平台名称重复：{key}")
        self.contact_data[self.contact_index] = (key, self.contact_value.get().strip())
        self.contact_list.delete(self.contact_index)
        self.contact_list.insert(self.contact_index, key)
        self.contact_list.selection_set(self.contact_index)

    def save_current_author(self) -> None:
        if self.author_index is None:
            return
        self.save_current_contact()
        author = self.authors_data[self.author_index]
        author["name"] = self.author_vars["name"].get()
        author["role"] = self.author_vars["role"].get()
        author["comment"] = self._text(self.author_comment)
        author["avatar"] = self.author_vars["avatar"].get().strip()
        if self.contact_data or "contact" in author:
            author["contact"] = dict(self.contact_data)
        self.author_list.delete(self.author_index)
        self.author_list.insert(self.author_index, author["name"] or "未命名作者")
        self.author_list.selection_set(self.author_index)

    def select_contact(self, index: int | None) -> None:
        if index == self.contact_index:
            return
        self.save_current_contact()
        self.contact_index = index
        self.contact_list.selection_clear(0, "end")
        if index is None:
            self.contact_key.set("")
            self.contact_value.set("")
        else:
            key, value = self.contact_data[index]
            self.contact_key.set(key)
            self.contact_value.set(value)
            self.contact_list.selection_set(index)

    def on_contact_selected(self, _event=None) -> None:
        selected = self.contact_list.curselection()
        if selected and selected[0] != self.contact_index:
            try:
                self.select_contact(selected[0])
            except ValueError as exc:
                messagebox.showerror("链接错误", str(exc), parent=self)
                if self.contact_index is not None:
                    self.contact_list.selection_set(self.contact_index)

    def add_contact(self) -> None:
        if self.author_index is None:
            return
        try:
            self.save_current_contact()
        except ValueError as exc:
            messagebox.showerror("链接错误", str(exc), parent=self)
            return
        new_key = "新平台"
        count = 2
        while any(key == new_key for key, _ in self.contact_data):
            new_key = f"新平台 {count}"
            count += 1
        self.contact_data.append((new_key, ""))
        self.contact_list.insert("end", new_key)
        self.contact_index = None
        self.select_contact(len(self.contact_data) - 1)

    def remove_contact(self) -> None:
        if self.contact_index is None:
            return
        index = self.contact_index
        del self.contact_data[index]
        self.contact_list.delete(index)
        self.contact_index = None
        self.select_contact(min(index, len(self.contact_data) - 1) if self.contact_data else None)

    def select_author(self, index: int | None) -> None:
        if index == self.author_index:
            return
        self.save_current_author()
        self.author_index = index
        self.author_list.selection_clear(0, "end")
        self.contact_index = None
        self.contact_data = []
        self.contact_list.delete(0, "end")
        if index is None:
            for var in self.author_vars.values():
                var.set("")
            self._set_text(self.author_comment, "")
            self.contact_key.set("")
            self.contact_value.set("")
            self.avatar_preview.config(image="", text="暂无头像")
            self.avatar_image = None
            return
        author = self.authors_data[index]
        self.author_vars["name"].set(str(author.get("name", "")))
        self.author_vars["role"].set(str(author.get("role", "")))
        self.author_vars["avatar"].set(str(author.get("avatar", "")))
        self._set_text(self.author_comment, str(author.get("comment", "")))
        contacts = author.get("contact", {})
        if not isinstance(contacts, dict):
            raise ValueError("作者 contact 必须是 JSON 对象。")
        self.contact_data = [(str(key), str(value)) for key, value in contacts.items()]
        for key, _ in self.contact_data:
            self.contact_list.insert("end", key)
        self.author_list.selection_set(index)
        self.select_contact(0 if self.contact_data else None)
        self.preview_avatar()

    def on_author_selected(self, _event=None) -> None:
        selected = self.author_list.curselection()
        if selected and selected[0] != self.author_index:
            try:
                self.select_author(selected[0])
            except ValueError as exc:
                messagebox.showerror("作者信息错误", str(exc), parent=self)
                if self.author_index is not None:
                    self.author_list.selection_set(self.author_index)

    def add_author(self) -> None:
        try:
            self.save_current_author()
        except ValueError as exc:
            messagebox.showerror("作者信息错误", str(exc), parent=self)
            return
        self.authors_data.append({"name": "", "role": "", "comment": "", "avatar": "", "contact": {}})
        self.author_list.insert("end", "未命名作者")
        self.author_index = None
        self.select_author(len(self.authors_data) - 1)

    def remove_author(self) -> None:
        if self.author_index is None:
            return
        index = self.author_index
        del self.authors_data[index]
        self.author_list.delete(index)
        self.author_index = None
        self.select_author(min(index, len(self.authors_data) - 1) if self.authors_data else None)

    def choose_avatar(self) -> None:
        if self.author_index is None:
            return
        chosen = filedialog.askopenfilename(
            title="选择头像图片", initialdir=self.current_path.parent if self.current_path else self.root_dir,
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp *.avif *.gif *.bmp *.tif *.tiff"),
                ("所有文件", "*.*"),
            ],
        )
        if not chosen:
            return
        source = Path(chosen)
        try:
            if Image is not None:
                with Image.open(source) as picture:
                    picture.verify()
            elif source.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("此图片格式需要 Pillow。请运行 python -m pip install pillow")
        except (OSError, ValueError) as exc:
            messagebox.showerror("无法使用头像", str(exc), parent=self)
            return
        relative = f"avatar/{source.stem}_{uuid4().hex[:8]}.png"
        self.pending_avatars[relative] = source
        self.author_vars["avatar"].set(relative)
        self.preview_avatar()

    def preview_avatar(self) -> None:
        relative = self.author_vars["avatar"].get().strip()
        if not relative:
            self.avatar_preview.config(image="", text="暂无头像")
            self.avatar_image = None
            return
        path = self.pending_avatars.get(relative)
        if path is None:
            path = Path(relative)
            if not path.is_absolute() and self.current_path:
                path = self.current_path.parent / path
        try:
            if not path.is_file():
                raise FileNotFoundError(path)
            if Image is not None and ImageTk is not None:
                with Image.open(path) as source:
                    preview = source.copy()
                preview.thumbnail((80, 80))
                self.avatar_image = ImageTk.PhotoImage(preview, master=self)
            else:
                image = tk.PhotoImage(file=str(path))
                factor = max(1, (max(image.width(), image.height()) + 79) // 80)
                self.avatar_image = image.subsample(factor)
            self.avatar_preview.config(image=self.avatar_image, text="")
        except (OSError, ValueError, tk.TclError):
            self.avatar_image = None
            note = "头像文件不存在" if not path.is_file() else "无法预览此格式（可安装 Pillow）"
            self.avatar_preview.config(image="", text=note)

    def copy_pending_avatars(self, metadata: dict) -> None:
        assert self.current_path is not None
        used = {a.get("avatar") for a in metadata.get("authors", []) if isinstance(a, dict)}
        for relative, source in self.pending_avatars.items():
            if relative not in used:
                continue
            if not source.is_file():
                raise FileNotFoundError(f"头像源文件不存在：{source}")
            destination = self.current_path.parent / relative
            if destination.exists():
                raise FileExistsError(f"头像目标文件已存在：{destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp_name = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=destination.parent, prefix=".avatar-", suffix=".png", delete=False
                ) as stream:
                    temp_name = stream.name
                if Image is not None and ImageOps is not None:
                    with Image.open(source) as picture:
                        converted = ImageOps.exif_transpose(picture).convert("RGBA")
                        converted.save(temp_name, format="PNG")
                else:
                    if source.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                        raise ValueError("此图片格式需要 Pillow。请运行 python -m pip install pillow")
                    shutil.copyfile(source, temp_name)
                os.replace(temp_name, destination)
            finally:
                if temp_name and os.path.exists(temp_name):
                    os.unlink(temp_name)

    def form_metadata(self) -> dict:
        assert self.model is not None
        metadata = copy.deepcopy(self.working_metadata)
        self.save_current_author()
        metadata["authors"] = copy.deepcopy(self.authors_data)
        metadata["name"] = self.vars["name"].get()
        metadata["tips"] = self._text(self.tips)
        license_info = metadata.setdefault("license", {})
        links = metadata.setdefault("link", {})
        if not isinstance(license_info, dict) or not isinstance(links, dict):
            raise ValueError("license 和 link 必须是 JSON 对象；请在高级 JSON 中修正。")
        license_info["type"] = self.vars["license_type"].get()
        license_info["desc"] = self.vars["license_desc"].get()
        links["home"] = self.vars["home"].get()
        links["donate"] = self.vars["donate"].get()
        return metadata

    def raw_metadata(self) -> dict:
        metadata = json.loads(self._text(self.raw))
        if not isinstance(metadata, dict):
            raise ValueError("metadata 必须是 JSON 对象。")
        return metadata

    def show_form(self, metadata: dict) -> None:
        license_info = metadata.get("license", {})
        links = metadata.get("link", {})
        if not isinstance(license_info, dict) or not isinstance(links, dict):
            raise ValueError("license 和 link 必须是 JSON 对象。")
        values = {
            "name": metadata.get("name", ""),
            "license_type": license_info.get("type", ""),
            "license_desc": license_info.get("desc", ""),
            "home": links.get("home", ""),
            "donate": links.get("donate", ""),
        }
        for key, value in values.items():
            self.vars[key].set(str(value))
        self._set_text(self.tips, str(metadata.get("tips", "")))
        authors = metadata.get("authors", [])
        if not isinstance(authors, list) or any(not isinstance(a, dict) for a in authors):
            raise ValueError("authors 必须是由 JSON 对象组成的数组。")
        self.authors_data = copy.deepcopy(authors)
        self.author_index = None
        self.author_list.delete(0, "end")
        for author in self.authors_data:
            self.author_list.insert("end", str(author.get("name", "未命名作者")))
        self.select_author(0 if authors else None)

    def show_raw(self, metadata: dict) -> None:
        self._set_text(self.raw, json.dumps(metadata, ensure_ascii=False, indent=2))
        self.raw_dirty = False

    def on_tab_changed(self, _event=None) -> None:
        if self.switching or self.model is None:
            return
        target = self.tabs.index(self.tabs.select())
        if target == self.active_tab:
            return
        try:
            if target == 1:
                metadata = self.form_metadata()
                self.working_metadata = metadata
                self.show_raw(metadata)
            else:
                metadata = self.raw_metadata()
                self.show_form(metadata)
                self.working_metadata = metadata
        except (ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("JSON 格式错误", str(exc), parent=self)
            self.switching = True
            self.tabs.select(self.active_tab)
            self.switching = False
            return
        self.active_tab = target

    def open_file(self, path: Path) -> None:
        if path.name.lower() != "ysm.json":
            messagebox.showerror("文件错误", "请选择解密模型目录中的 ysm.json。", parent=self)
            return
        if self.model is not None and not self.confirm_discard():
            return
        try:
            model = read_model(path)
            metadata = model.get("metadata", {})
            self.show_form(metadata)
            self.show_raw(metadata)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("打开失败", str(exc), parent=self)
            return
        self.model = model
        self.working_metadata = copy.deepcopy(metadata)
        self.current_path = path
        self.pending_avatars = {}
        self.preview_avatar()
        self.switching = True
        self.tabs.select(0)
        self.switching = False
        self.active_tab = 0
        self.file_label.config(text=str(path))
        self.status.config(text="已打开；编辑后按 Ctrl+S 保存")

    def has_changes(self) -> bool:
        if self.model is None:
            return False
        try:
            metadata = self.raw_metadata() if self.active_tab else self.form_metadata()
        except (ValueError, json.JSONDecodeError):
            return True
        return metadata != self.model.get("metadata", {})

    def confirm_discard(self) -> bool:
        return not self.has_changes() or messagebox.askyesno(
            "未保存的修改", "当前模型有未保存的修改，确定放弃吗？", parent=self
        )

    def save(self, _event=None) -> None:
        if self.model is None or self.current_path is None:
            messagebox.showinfo("提示", "请先打开一个 ysm.json。", parent=self)
            return
        try:
            metadata = self.raw_metadata() if self.active_tab else self.form_metadata()
            updated = replace_metadata(self.model, metadata)
            self.copy_pending_avatars(metadata)
            backup = save_model(
                self.current_path, updated, create_backup=not self.no_backup.get()
            )
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)
            return
        self.model = updated
        self.working_metadata = copy.deepcopy(metadata)
        self.pending_avatars = {}
        self.show_form(metadata)
        self.show_raw(metadata)
        backup_note = f"备份：{backup.name}" if backup else "未生成 .bak 备份"
        self.status.config(text=f"保存成功；{backup_note}")
        messagebox.showinfo(
            "保存成功", f"已保存 {self.current_path.name}\n{backup_note}", parent=self
        )

    def on_close(self) -> None:
        if self.confirm_discard():
            self.batch_panel.shutdown()
            self.destroy()


if __name__ == "__main__":
    Editor().mainloop()
