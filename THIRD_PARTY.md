# 第三方代码与依赖

本目录中的第三方代码用于构建和运行。原始项目目录未被修改。
根目录 `LICENSE` 适用于本工具原创代码；下表中的第三方代码保留各自许可证。

| 组件 | 本地位置 | 来源 / 版本 | 许可文件 |
|---|---|---|---|
| YSMParser | `native/YSMParser/` | [OpenYSM/YSMParser](https://github.com/OpenYSM/YSMParser) 的本地源码快照，含本工具的反渲染开关和 Unicode 路径修复 | `native/YSMParser/LICENSE.txt` |
| OpenYSM 部分 Java 源码 | `third_party/openysm-src/` | [OpenYSMDev/ModernYSM](https://github.com/OpenYSMDev/ModernYSM) 的 `ModernYSM-1.20.1-forge` 本地快照；48 个实际编译的 Java 文件，逐文件哈希见 `SOURCE_MANIFEST.json` | `third_party/openysm-src/LICENSE.txt` |
| Gson | `third_party/java-libs/gson-2.10.1.jar` | [google/gson](https://github.com/google/gson/tree/gson-parent-2.10.1) 2.10.1 | `third_party/licenses/gson-2.10.1-LICENSE.txt` |
| JOML | `third_party/java-libs/joml-1.10.5.jar` | [JOML-CI/JOML](https://github.com/JOML-CI/JOML) 1.10.5 | `third_party/licenses/joml-1.10.5-LICENSE.txt`（取自 JAR） |
| Netty Buffer / Common | `third_party/java-libs/netty-*.jar` | [netty/netty](https://github.com/netty/netty/tree/netty-4.1.110.Final) 4.1.110.Final | `third_party/licenses/netty-4.1.110.Final-LICENSE.txt`、`netty-4.1.110.Final-NOTICE.txt` |
| Python、Pillow、PyInstaller | 构建环境及发布包 | 见 `requirements-build.txt` 和 `SOURCE_BUILD.md` | `third_party/licenses/` |

YSMParser 的 `external/` 目录包含 C++ 构建依赖及原附许可文件；其许可副本存放于 `third_party/licenses/native/`。Java JAR 的 SHA-256 见 `third_party/java-libs/SHA256SUMS.json`，构建时会校验。

OpenYSM 和 YSMParser 的本地源码目录没有 Git 提交记录，因此本快照记录了来源项目、目录版本和文件哈希，未声称对应某个未经核实的提交。若以后更新快照，须同步更新来源、哈希和许可文件。
