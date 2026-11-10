# 从源码构建（Windows x64）

本仓库包含 GUI Python 代码、修改后的 YSMParser C++ 源码、加密所需的 OpenYSM Java 源码快照、固定版本 Java JAR 和第三方许可文件。构建结果写入被 Git 忽略的 `bin/`、`.build/`、`Release/`。

## 工具

- Python 3.14（当前构建验证版本）
- Visual Studio 2022 C++ 编译工具、CMake
- JDK 17 或更高版本，`java`、`javac`、`jar` 可用
- `pip install -r requirements-build.txt`

如果 CMake 不在 `PATH` 中，可设置 `CMAKE` 环境变量为 `cmake.exe` 的完整路径。

## 一键构建

```powershell
python build_all.py
```

它依次执行：

1. `build_parser.py`：从 `native/YSMParser` 编译，输出 `bin/YSMParser.exe`。
2. `build_encryptor.py`：从 `third_party/openysm-src` 和 `java/` 编译，先校验固定 JAR 的 SHA-256，输出 `bin/encryptor/ysm-encryptor.jar`。
3. `build_release.py`：打包 GUI 和独立的 `BatchEncrypt.exe`，输出 `Release/YSMMetadataEditor/`，并附上 `licenses/`。

也可以逐个运行上述脚本。源码运行 GUI：`python ysm_metadata_editor.py`。发布目录使用 `YSMMetadataEditor.exe` 启动，须保留同目录其他文件。

当前发布目录**不含 Java 运行时**，批量加密要求目标电脑安装 Java 17 或更高版本。

## 源码与构建产物

`native/YSMParser`、`third_party/openysm-src`、`java`、根目录 Python 和构建脚本属于源码。`bin/`、`.build/`、`Release/` 是生成物，不需要提交到源码仓库。测试模型和个人设置不在源码包中。
