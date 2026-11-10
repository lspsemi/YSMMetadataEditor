# YSM 模型元数据编辑器

用 Python Tkinter 编辑**解密模型目录**中的 `ysm.json` 元数据。

本目录是可独立构建的源码发布版：YSMParser C++ 源码位于 `native/YSMParser`，加密所需 OpenYSM Java 源码位于 `third_party/openysm-src`。构建不依赖 D 盘原有项目、符号链接或预先编译的 `bin`。详见 [SOURCE_BUILD.md](SOURCE_BUILD.md) 和 [THIRD_PARTY.md](THIRD_PARTY.md)。

## 运行

在 Windows 上双击 `启动编辑器.bat` 即可启动 GUI。也可以在命令行运行：

```powershell
python ysm_metadata_editor.py
```

头像预览和替换支持 PNG、JPEG、WebP、AVIF、GIF、BMP、TIFF 等图片格式。选择新头像后，保存时统一转成真正的 PNG。非 PNG 格式需要 Pillow：`python -m pip install pillow`。不安装 Pillow 时，仍可选择和预览普通 PNG。

首次启动时选择解密模型目录，程序会记住该目录，下次启动自动打开。双击左侧模型打开，也可以直接打开 `ysm.json`。设置保存在当前用户的本地应用数据目录中，不会写入模型文件夹。

基础信息页可编辑模型名称、提示、授权和链接。作者区域可添加或删除作者，用输入框修改姓名、职责、简介、头像路径，以及每位作者的联系方式平台和链接。点击“选择头像”可选图片并预览；保存时程序会将图片转换为 PNG，放入模型的 `avatar` 目录，并更新该作者的头像路径。动图只取第一帧。高级页可编辑完整的 `metadata` 对象。切换页面时会同步编辑内容并检查 JSON 格式。

按 **Ctrl+S** 保存。元数据编辑页只修改 `metadata`，保留 `spec`、`properties`、`files` 等其他内容。默认在同目录创建带时间戳的 `ysm.json.*.bak` 备份；勾选“**不生成 .bak 文件**”后保存则跳过备份，该选项默认未勾选。`.ysm` 文件请在批量加解密页处理。

## 批量加解密

窗口上方的“**批量加解密**”页提供两种操作：

- **批量解密**：递归处理输入目录中的 `.ysm`，每个模型输出到同名文件夹。默认勾选“解密时应用反渲染”，输出可编辑的 Blockbench 立方体；取消勾选则保留原始面的顶点、法线和 UV（`ysm_raw_faces`），此时模型 JSON 不是可直接编辑的 Blockbench 立方体。该开关只影响 V3 模型。
- **批量加密**：递归处理含 `ysm.json` 的解密模型文件夹，输出同名 `.ysm`。已有的输出文件会跳过，避免覆盖。加密过程使用临时副本，图片资源在临时副本中统一转为 PNG，原模型文件不会修改。

解密调用构建生成的 `bin/YSMParser.exe`。加密调用根据本仓库 OpenYSM 源码构建的 `bin/encryptor/ysm-encryptor.jar`，需要 **Java 17 或更高版本**；非 PNG 图片还需要 Pillow。运行 `python build_encryptor.py` 可重新构建加密组件。

## Windows 打包

安装 PyInstaller 和 Pillow 后运行 `python build_release.py`，可在 `Release/YSMMetadataEditor` 得到 GUI 目录。打包版的批量加密由目录中的 `BatchEncrypt.exe` 处理；源码运行仍使用 `batch_encrypt.py`。不要只复制 GUI 的 exe，需保留发布目录中的 `bin` 和其他文件。当前加密功能仍要求用户安装 Java 17 或更高版本。
