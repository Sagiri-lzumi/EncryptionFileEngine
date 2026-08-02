# Encryption Studio 项目深度解析

> 本文件是对整个 Encryption Studio 仓库的**完整开发者级技术解读**，面向接手维护或二次开发的工程师。所有结论均直接来源于仓库当前源码（C:\EncryptionFileEngine），不依赖任何已失效的外部描述。文档以 UTF-8 编码保存。

---

## 目录

1. [项目定位与一句话概述](#1-项目定位与一句话概述)
2. [整体架构总览](#2-整体架构总览)
3. [项目目录结构](#3-项目目录结构)
4. [模块依赖关系总图](#4-模块依赖关系总图)
5. [入口层：main.py](#5-入口层mainpy)
6. [全局配置：config.py](#6-全局配置configpy)
7. [核心加密层 core/](#7-核心加密层-core)
   - 7.1 [cipher_base.py — 加密抽象基类](#71-cipher_basepy--加密抽象基类)
   - 7.2 [aes_cipher.py — AES-256-CBC 工具类](#72-aes_cipherpy--aes-256-cbc-工具类)
   - 7.3 [file_format.py — 加密文件格式 V2](#73-file_formatpy--加密文件格式-v2)
   - 7.4 [file_cipher.py — 老系统文件加密引擎](#74-file_cipherpy--老系统文件加密引擎)
   - 7.5 [rsa_cipher.py — RSA 混合加密与密钥管理](#75-rsa_cipherpy--rsa-混合加密与密钥管理)
   - 7.6 [text_cipher.py — 文本加密与老系统兼容派生](#76-text_cipherpy--文本加密与老系统兼容派生)
   - 7.7 [logger.py — 单例日志服务](#77-loggerpy--单例日志服务)
8. [UI 层 ui/](#8-ui-层-ui)
   - 8.1 [themes.py — 设计令牌与主题切换](#81-themespy--设计令牌与主题切换)
   - 8.2 [platform_fonts.py — 跨平台字体适配](#82-platform_fontspy--跨平台字体适配)
   - 8.3 [native_effects.py — macOS 原生毛玻璃](#83-native_effectspy--macos-原生毛玻璃)
   - 8.4 [icons.py — 纯线稿图标引擎](#84-iconspy--纯线稿图标引擎)
   - 8.5 [components.py — 自定义 UI 组件库](#85-componentspy--自定义-ui-组件库)
   - 8.6 [splash.py — 启动动画](#86-splashpy--启动动画)
   - 8.7 [utils.py — 跨平台工具函数](#87-utilspy--跨平台工具函数)
9. [主窗口 ui/main_window.py](#9-主窗口-uimain_windowpy)
   - 9.1 [模块整体结构](#91-模块整体结构)
   - 9.2 [辅助函数与目录名加密](#92-辅助函数与目录名加密)
   - 9.3 [BatchWorkerThread — 老系统批量线程](#93-batchworkerthread--老系统批量线程)
   - 9.4 [RSABatchWorkerThread — 新系统批量线程](#94-rsabatchworkerthread--新系统批量线程)
   - 9.5 [MainWindow — 主窗口架构](#95-mainwindow--主窗口架构)
   - 9.6 [页面与视图体系](#96-页面与视图体系)
   - 9.7 [主题系统与 macOS 毛玻璃](#97-主题系统与-macos-毛玻璃)
   - 9.8 [系统托盘与生命周期](#98-系统托盘与生命周期)
   - 9.9 [RSA 密钥管理界面](#99-rsa-密钥管理界面)
   - 9.10 [信号槽全链路](#910-信号槽全链路)
10. [加密文件二进制格式规范](#10-加密文件二进制格式规范)
11. [多线程与多进程架构](#11-多线程与多进程架构)
12. [SSD 加速机制详解](#12-ssd-加速机制详解)
13. [跨平台适配策略](#13-跨平台适配策略)
14. [性能优化与分块策略](#14-性能优化与分块策略)
15. [错误处理与日志体系](#15-错误处理与日志体系)
16. [打包与构建](#16-打包与构建)
17. [已知边界情况与风险提示](#17-已知边界情况与风险提示)
18. [快速上手](#18-快速上手)

---

## 1. 项目定位与一句话概述

**Encryption Studio** 是一个基于 **Python + PySide6（Qt6）** 开发的**本地文件安全防御系统**桌面应用，核心能力是：

- **双加密系统并行**
  - **老系统**：AES-256-CBC 对称加密，口令即密钥，集成文件名混淆、目录名加密、智能分块、多进程批量。
  - **新系统**：RSA-2048 非对称 + AES 混合加密，公钥加密、私钥用口令保护，安全性更高。
- **大文件智能分块**（1MB / 10MB / 64MB 三档自适应），流畅处理 GB 级文件且内存占用极低。
- **界面 100% 不阻塞**：所有加解密通过 `QThread` + Qt 信号槽在后台执行，主线程只做渲染。
- **跨平台**：同一套代码在 Windows / macOS 运行，macOS 上启用原生 `NSVisualEffectView` 毛玻璃，其余平台用 QSS 拟态玻璃并安全降级。
- **现代苹果风 UI**：纯线稿图标自绘、圆角卡片、动画侧边栏、明暗主题跟随系统。

它本质是一个**“面向桌面终端用户、以文件批量加解密为业务、以 Qt 信号槽为线程协作骨架”的单体应用**。

---

## 2. 整体架构总览

项目采用经典的**三层分离架构**，严格遵循“UI 与业务逻辑解耦、耗时操作不进主线程”的原则：

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py  (入口编排)                     │
│   PyInstaller 冻结支持 / AppUserModelID / 启动动画 / 主窗口      │
└───────────────┬───────────────────────────────┬──────────────┘
                │                               │
        ┌───────▼────────┐              ┌──────▼─────────┐
        │   config.py     │              │     ui/         │
        │  BASE_DIR / DIRS │              │  视图与线程层   │
        │  路径基准 + 建目录 │              │ (PySide6 全部) │
        └───────┬──────────┘              └──────┬─────────┘
                │                                │
                │         ┌──────────────────────┘
                │         │
        ┌───────▼─────────▼───┐
        │       core/          │
        │   加密核心业务逻辑层  │
        │  (cryptography 库)   │
        └──────────────────────┘
```

**三层职责：**

| 层 | 目录 | 职责 | 是否含 Qt |
|----|------|------|-----------|
| **入口/配置层** | `main.py`、`config.py` | 进程启动、跨进程冻结支持、路径基准、目录初始化 | main.py 用 QApplication；config.py 纯标准库 |
| **核心业务层** | `core/` | 所有加密算法、文件格式、密钥管理、日志；不依赖任何 UI | 否（纯 `cryptography` + 标准库），仅 logger 读取 config |
| **UI 与线程层** | `ui/` | 视图、自定义控件、主题、字体、原生特效、后台工作线程、托盘 | 是 |

**关键设计纪律（贯穿全仓）：**

1. **UI 绝不直接做加解密**：加解密一律通过 `BatchWorkerThread` / `RSABatchWorkerThread`（继承 `QThread`）在后台执行，结果经 Qt Signal 回到主线程。
2. **路径绝不硬编码斜杠**：全部使用 `os.path.join` / `os.path.dirname` 等，Windows 长路径通过 `ui/utils.py::ensure_long_path` 加 `\\?\` 前缀修复。
3. **核心层零 Qt 依赖**：`core/` 不 import PySide6，可被独立测试或脚本复用。
4. **失败必须降级而非崩溃**：macOS 毛玻璃、多进程 IPC、任何原生调用失败都静默降级，不影响主流程。

---

## 3. 项目目录结构

以下是仓库根目录的实际结构与每个条目的职责（来源于实际文件列表）：

```
EncryptionFileEngine/
├── main.py                入口：冻结支持、AppUserModelID、启动动画编排、主窗口
├── config.py              全局配置：BASE_DIR 自适应、DIRS 目录注册、init_directories()
├── core/                  核心业务逻辑层（无 Qt 依赖）
│   ├── __init__.py        空包标识
│   ├── cipher_base.py     加密抽象基类 CipherBase / FileCipherBase（ABC）
│   ├── aes_cipher.py      AES-256-CBC 静态工具类 AESCipher
│   ├── file_format.py     加密文件 V2 二进制头打包/解包 FileFormat
│   ├── file_cipher.py     老系统文件加密引擎 FileCipherEngine（含智能分块、暂停/停止）
│   ├── rsa_cipher.py      新系统：RSAKeyManager + RSAFileCipher 混合加密
│   ├── text_cipher.py     文本加密 TextCipher + 老系统多算法兼容派生
│   └── logger.py          单例日志服务 LoggerService
├── ui/                    UI 与线程层（PySide6）
│   ├── __init__.py        空包标识
│   ├── themes.py          设计令牌 + THEMES 字典(Light/Dark) + 几何常量
│   ├── platform_fonts.py  跨平台字体族选择与 QSS 生成
│   ├── native_effects.py  macOS NSVisualEffectView 原生毛玻璃封装 NativeGlassController
│   ├── icons.py           自绘线稿图标引擎 draw_icon() / make_icon()
│   ├── components.py      24+ 个自定义控件（一文件组件库）
│   ├── splash.py          启动动画 IntroScreen
│   ├── utils.py           ensure_long_path / format_size / get_drive_root
│   └── main_window.py     主窗口 + 两个 BatchWorker 线程类（约 2692 行，项目核心）
├── assets/                资源目录
├── PNG/                   截图（img/img_1/img_2/img_3.png）
├── Keys/                  RSA 密钥对存储目录（运行期生成）
├── Logs/                  日志输出目录（运行期生成，RollingFile 10MB×5）
├── OriginalFile/          老系统源文件工作区
├── DecryptedFile/         解密输出工作区
├── TempCache/             临时缓存
├── AuthDate/              授权数据（历史遗留）
├── build/                 构建中间产物
├── dist/                  PyInstaller 打包产物
├── .venv/                 虚拟环境
├── .idea/                 PyCharm 工程
├── .claude/               Claude 配置
├── .git/                  Git 仓库
├── docs/                  开发者文档
│   ├── README.md          文档索引
│   ├── setup.md           环境依赖与安装说明
│   ├── technical-reference.md 开发者技术参考手册
│   └── architecture-deep-dive.md 本文件（全面深度解析）
├── scripts/               开发辅助脚本
│   └── export_code.py     代码导出工具（生成 all_code.txt，被 .gitignore 忽略）
├── tests/                 测试与实验脚本
│   └── test_checkbox.py   复选框控件的独立测试脚本
├── EncryptionStudio.spec  PyInstaller 打包规格
├── all_code.txt           全仓源码合并文本（由 export_code.py 产出，被 .gitignore 忽略）
├── requirements.txt        运行依赖（PySide6/cryptography/pyobjc/pyinstaller/cx_Freeze/Nuitka）
├── requirements-macos.txt macOS 依赖
├── requirements-dev.txt   开发依赖
├── fileenc.ico            应用图标
├── LICENSE                许可证
├── .gitignore / .gitattributes
├── AGENTS.md              Codex/Agent 协作规范
└── README.md              项目介绍（面向用户，含截图）
```

> 说明：`technical-reference.md` 与 `README.md` 的中文内容用 GB18030 写入但部分工具按 UTF-8 读取会出现乱码；本文件全部以 UTF-8 重新编写，以当前源码为唯一事实来源。

---

## 4. 模块依赖关系总图

以下是真实存在的 import 关系（箭头表示“依赖/导入”）：

```
main.py
 ├── config (init_directories, BASE_DIR)
 ├── ui.splash (IntroScreen)
 └── ui.main_window (MainWindow)

ui.main_window
 ├── config (DIRS)
 ├── core.file_cipher (FileCipherEngine)
 ├── core.logger (sys_logger)
 ├── ui.themes (THEMES, 几何常量)
 ├── ui.native_effects (NativeGlassController)
 ├── ui.components (全部自定义控件)
 ├── ui.platform_fonts
 └── ui.utils (ensure_long_path, format_size, get_drive_root)

ui.main_window.BatchWorkerThread.run()
 └── core.file_cipher.FileCipherEngine.process_file_direct()  （经 task_wrapper 到子进程）

ui.main_window.RSABatchWorkerThread.run()
 └── core.rsa_cipher.RSAFileCipher.encrypt_file / decrypt_file

core.rsa_cipher
 └── core.logger (sys_logger)

core.file_cipher
 └── core.logger (sys_logger)

core.logger
 └── config (DIRS["LOGS"])

ui.components / ui.splash
 └── ui.themes, ui.icons, ui.platform_fonts   (仅 UI 内部依赖)

core/aes_cipher.py、core/cipher_base.py、core/file_format.py
 └── 仅 cryptography / 标准库（最纯净，零项目内依赖）
```

**关键观察：**

- `core/` 形成一个无 Qt 的纯净业务核心，`logger` 是唯一向上读取 `config` 的模块。
- `ui/main_window.py` 是唯一同时连接“核心业务”与“UI 表现”的聚合点，是项目中最庞大也最关键的文件。
- `ui/components.py` 与 `ui/main_window.py` 之间是“控件库 vs 控件使用者”的清晰边界，组件库不反向依赖主窗口。
- `core/text_cipher.py` 是为兼容“老版文本加密产物”而存在的派生模块，内部支持 AES/3DES/RC4 多算法与 PBKDF2 派生。

---

## 5. 入口层：main.py

`main.py` 约 40 行，职责单一且被严格约束（见 `main()` 流程）：

1. **`multiprocessing.freeze_support()`**：必须在 `QApplication` 初始化之前调用，否则 PyInstaller 打包后的 Windows 多进程会反复触发入口函数导致程序反复弹窗/崩溃。这是 `core/file_cipher` 走 `ProcessPoolExecutor` 的前置条件。
2. **Windows `AppUserModelID` 注册**：`ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('security.fileengine.cipher.1.0')`，让 Windows 任务栏把本进程识别为独立应用并正确显示 `fileenc.ico` 图标。仅 `sys.platform == 'win32'` 时执行，非 Windows 自动跳过。
3. **`init_directories()`**：调用 `config.py` 创建 `Keys/`、`Logs/` 等必需目录。
4. **`QApplication` 初始化**，设置全局应用图标（`fileenc.ico`，存在性检查后才设置，丢失不崩溃）。
5. **启动动画 `IntroScreen`**：显示后用 `for i in range(1,51)` 模拟加载进度（0→100%），前半段文案 `LOADING KERNEL...`，后半段 `STARTING UI...`；每步 `QThread.msleep(10)` + `app.processEvents()`，确保启动动画在主线程正常渲染而不“卡住”。
6. **`MainWindow` 创建并 `show()`**，`splash.finish(window)` 收尾，`sys.exit(app.exec())` 进入事件循环。

设计要点：入口只做“编排”，不写业务；图标加载做了存在性兜底；`freeze_support` 位置是 PyInstaller 多进程成败的关键。

---

## 6. 全局配置：config.py

`config.py` 约 18 行，是整个项目的**路径基准与目录注册中心**：

- **`BASE_DIR` 自适应**：
  - 打包环境（`getattr(sys, 'frozen', False)` 为 True，即 PyInstaller 运行时）→ `os.path.dirname(sys.executable)`，即 `.exe` 所在目录。
  - 开发环境（普通 Python 运行）→ `os.path.dirname(os.path.abspath(__file__))`，即 `config.py` 所在目录。
  - **设计意图**：无论开发还是打包分发，所有数据文件（日志、密钥、加解密输出）都始终落在**可执行文件旁**，而不是散落到系统临时目录，便于携带与清理。
- **`DIRS` 目录注册表**（`os.path.join` 拼接，返回 `str`）：
  - `KEYS` → `Keys/`：RSA 密钥对存储。
  - `LOGS` → `Logs/`：日志文件。
  - 注：`OriginalFile`、`DecryptedFile`、`TempCache` 等工作区由 UI 在用户操作时按需创建，未在 `DIRS` 中硬性声明。
- **`init_directories()`**：遍历 `DIRS.values()`，不存在则 `os.makedirs` 创建（用 `os.path.exists` 判断，行为等价于 `exist_ok=True`）。

> 注意历史差异：`technical-reference.md` 描述过更完整的 `DIRS`（含 ORIGINAL/ENCRYPTED/DECRYPTED/CHUNK_SIZES 等），但当前 `config.py` 已精简为 `KEYS` / `LOGS` 两项，其余路径在 `main_window.py` 内按需用 `os.path` 动态拼装。本文件以**当前源码**为准。

---

## 7. 核心加密层 core/

本层是整个项目最纯净的部分：除 `logger.py` 读取 `config.DIRS` 外，其余模块**零项目内依赖**，只依赖 `cryptography` 与标准库。这使得核心加密逻辑可被脚本化复用或独立单元测试。

### 7.1 cipher_base.py — 加密抽象基类

定义两段抽象契约，约束所有加密实现的统一返回值结构，便于上层多态调度：

- **`CipherBase(ABC)`**：
  - `encrypt(data: bytes, **kwargs) -> Tuple[bool, str, bytes]`：返回 `(成功标志, 消息, 密文/明文)`。
  - `decrypt(data: bytes, **kwargs) -> Tuple[bool, str, bytes]`：同上。
- **`FileCipherBase(CipherBase)`**：追加文件级接口：
  - `encrypt_file(input_path, output_path, key, callback=None, **kwargs) -> Tuple[bool, str]`。
  - `decrypt_file(...)` 同形。
  - `callback` 为进度回调（由 `BatchWorkerThread` 注入，实现 UI 进度反馈）。

> 当前 `FileCipherEngine` 与 `RSAFileCipher` 实际实现并未显式继承这些抽象类，而是按“鸭子类型”实现了同名方法。抽象基类主要承担**接口文档化**作用，并为将来重构提供类型约束。

### 7.2 aes_cipher.py — AES-256-CBC 工具类

`AESCipher` 是一组静态方法，是无状态的 AES-256-CBC 最小工具：

- `generate_key()` → `os.urandom(32)`：32 字节 AES-256 密钥。
- `generate_iv()` → `os.urandom(16)`：16 字节 CBC IV。
- `encrypt(plaintext, key, iv)`：PKCS7(128bit) 填充 → `Cipher(AES(key), CBC(iv))` 加密 → 返回密文。
- `decrypt(ciphertext, key, iv)`：反向解密 → 去 PKCS7 填充 → 返回明文。

> 该类主要被 `rsa_cipher.py` 的混合加密复用（用 AES 加密文件内容，用 RSA 加密 AES 密钥）。`file_cipher.py` 的老系统则为追求大宗量 IO 性能，直接调 `Cipher` 而未走 `AESCipher`，但算法与填充策略与之完全一致。

### 7.3 file_format.py — 加密文件格式 V2

`FileFormat` 定义新系统 V2 加密头的二进制规范：

- **魔术字**：`MAGIC_V2 = b"ENC2"`（4 字节），用于解密时识别格式版本。
- **`pack_v2_header(iv, metadata) -> bytes`**：打包格式 `[MAGIC(4)] + [VERSION(1)] + [IV_LEN(1)] + [IV] + [METADATA_LEN(4)] + [METADATA_JSON(UTF-8)]`，用 `struct.pack` 大端编码。
- **`unpack_v2_header(data) -> (version, iv, metadata)`**：反向解包，校验魔术字不符则抛 `ValueError("Invalid V2 format")`，metadata 用 `json.loads` 解析。
- **`is_v2_format(data) -> bool`**：读前 4 字节判断是否 V2。

> 这是新系统（RSA 混合）的文件格式底座：IV 与元数据（含原始文件名、算法等）被打入文件头，解密时先识别版本再分派解包路径，从而兼容未来格式演进。

### 7.4 file_cipher.py — 老系统文件加密引擎

`FileCipherEngine` 是老系统的文件级 AES-256-CBC 引擎，是项目里**最贴近“大文件 I/O 性能”**的模块。核心方法 `process_file_direct()` 既支持加密也支持解密（由 `is_encrypt` 分派），并内建暂停/停止/进度回调/异常清理。

**加密流程（`is_encrypt=True`）：**

1. 存在性检查 + 输出目录自动 `os.makedirs`。
2. `file_size = os.path.getsize`，`chunk_size = self._get_smart_chunk_size(file_size)` 智能分块。
3. 若 `encrypt_filename=True`：生成随机名 `uuid.uuid4().hex[:12] + ".enc"` 落到目标目录。
4. 生成 16 字节 `iv`，构造 `Cipher(AES(key), CBC(iv))`，准备 PKCS7 padder。
5. **文件名加密**：把原始文件名以 AES-CBC(iv) 加密后打包进文件头，供解密时无损还原。
6. **写文件头**：`IV(16) + NameLen(4, big-end uint32) + EncNameBytes + OriginSize(8, big-end uint64)`。
7. **分块流式加密**：循环 `f_in.read(chunk_size)` → `encryptor.update(padder.update(chunk))` 写出；每块后 `callback(processed, file_size)` 回调进度；每块前检查 `controller.is_stop_requested()` 与 `controller.wait_if_paused()`，实现暂停/停止。
8. 文件尾：`encryptor.update(padder.finalize()) + encryptor.finalize()` 写入最后一块。
9. 成功返回 `(True, "加密成功", final_out_path)`。

**解密流程（`is_encrypt=False`）：**

1. 读 16 字节 IV（不足判“文件头损坏”）。
2. 读 4 字节 `name_len`，读加密文件名，AES-CBC 解出原始文件名（失败判“密钥错误或文件名元数据损坏”）。
3. **强制恢复原始文件名**：忽略传入的 `target_path` 的文件名部分，改用解出的 `orig_name` 拼接到 `target_dir`。
4. 跳过 8 字节原始大小。
5. 分块流式解密 + 去 PKCS7 填充，进度按 `total_file_size - header_size` 计算。
6. 末尾 `unpadder.update(decryptor.finalize()) + unpadder.finalize()`。
7. `ValueError` 判“数据损坏或填充错误”，其余异常进日志后报“解密异常”。

**异常与清理：**

- `InterruptedError("STOP")`（用户停止）→ `_cleanup_partial_output()` 删半成品 → 返回 `(False, "用户终止", "")`。
- 任何 `Exception` → 删半成品 + 写日志 → 返回 `(False, str(e), "")`。
- `_cleanup_partial_output()` 删除失败也写 warning 日志，绝不二次抛出。

**智能分块（`_get_smart_chunk_size`）：**

| 文件大小 | chunk_size | 策略意图 |
|----------|-----------|----------|
| < 100MB | 1MB | 小文件高频率分块，快速反馈进度 |
| < 2GB | 10MB | 中等文件平衡 I/O 与内存 |
| ≥ 2GB | 64MB | 超大文件减少系统调用、榨取吞吐 |

> 设计亮点：分块不是固定值而是按文件量级三档自适应，兼顾“小文件进度刷新快”与“大文件吞吐高”。进度回调与暂停/停止检查都在每个 chunk 边界发生，响应延迟 ≤ 一个 chunk 的处理时间。

### 7.5 rsa_cipher.py — RSA 混合加密与密钥管理

本模块是新系统的核心，包含两个类：

**`RSAKeyManager`（密钥管理，静态方法）：**

- `generate_key_pair(password, key_name="rsa_key") -> (private_pem, public_pem)`：
  - `rsa.generate_private_key(public_exponent=65537, key_size=2048)`。
  - 私钥用 `BestAvailableEncryption(password)` 加密后导出 PKCS8 PEM；公钥不加密导出 SubjectPublicKeyInfo PEM。
  - 返回两个 PEM 字节串，由 UI 落盘到 `Keys/{name}_private.pem` / `_public.pem`。
- `load_private_key(key_path, password)`：读 PEM 并用口令解锁，返回私钥对象。
- `load_public_key(key_path)`：读 PEM 公钥，返回公钥对象。

**`RSAFileCipher`（混合加密，静态方法）：**

- **加密（`encrypt_file`）= RSA 包 AES 密钥 + AES 加密文件内容**：
  - 生成随机 AES-256 会话密钥与 IV。
  - 用 RSA 公钥（OAEP + SHA-256）加密 AES 密钥。
  - 用 AES-256-CBC 加密文件内容（分块）。
  - 用 AES-CBC 加密原始文件名（与老系统同名逻辑同源，便于解密还原）。
  - 写出 V2 格式头（`FileFormat.pack_v2_header`）+ 加密的 AES 密钥 + 加密的文件名 + 加密的文件内容。
  - 支持 `callback` 进度、`_cleanup_partial_output` 异常清理。
- **解密（`decrypt_file`）**：
  - 用私钥（需口令解锁）解密 AES 会话密钥。
  - 用 AES 解密文件内容与文件名，强制恢复原始文件名路径。
  - 返回 `(success, msg, actual_out_path)`，供 UI 更正输出路径。

> 混合加密的意义：RSA 单次只能加密约 245 字节（OAEP/SHA-256/2048bit），无法直接加密文件；因此“RSA 包密钥、AES 包内容”——既享受非对称的密钥分发安全（公钥可公开、私钥口令保护），又享受 AES 的对称高吞吐。这是工业标准的 Hybrid Encryption 范式。

### 7.6 text_cipher.py — 文本加密与老系统兼容派生

`TextCipher` 是为**“文本加密”以及兼容老版多算法文本产物**而存在的模块，是全项目算法覆盖面最广的部分：

- **支持的算法**：AES、DES、3DES、RC4（其中 DES/3DES/RC4 通过 `cryptography` 的 `decrepit_algorithms` 访问，属于已被废弃但保留兼容的算法）。
- **密钥派生**：两条路径
  - 老系统：`SHA-256(password)` 后按算法 key_size 折叠/扩展（`_expand_key`）。
  - 新派生：`PBKDF2HMAC(SHA-256, salt, iterations)` 派生密钥。
- **编解码**：密文用 `base64.urlsafe_b64encode/decode` 包装为可传输文本。
- **异常处理**：解密失败统一抛 `ValueError("密码错误或密文损坏")`，避免向调用方泄漏内部细节。
- **用途**：为“文本加密”功能页提供底层，并能解密历史上的多算法加密文本，做到向后兼容。

> 注意：DES/3DES/RC4 仅用于**读取旧产物**的兼容性目的，不应再用于新加密。新文本加密默认走 AES + PBKDF2 派生路径。

### 7.7 logger.py — 单例日志服务

`LoggerService` 用 `__new__` 实现进程级单例（`_instance` + `_initialized` 双重锁），双通道输出：

- **文件通道**：`RotatingFileHandler`，路径 `DIRS["LOGS"]/Encrypt_{YYYYMMDD_HHMMSS}.log`，`maxBytes=10MB`、`backupCount=5`、`encoding='utf-8'`，避免日志把磁盘撑爆。
- **控制台通道**：`StreamHandler(sys.stdout)`，便于开发期调试。
- **格式**：`%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s`，时间精确到秒。
- **全局实例**：模块末尾 `sys_logger = LoggerService()`，供 `core.file_cipher`、`core.rsa_cipher`、`ui.main_window` 复用 `sys_logger.log(msg, level)` 接口。
- `propagate = False` 防止日志向上冒泡到 root logger 重复输出。

> 设计亮点：单例 + 滚动文件 + UTF-8 编码，既适合长期运行（自动轮转、不爆盘），也适合跨平台（统一 UTF-8，避免 Windows 控制台编码差异导致日志乱码）。

---

## 8. UI 层 ui/

UI 层是项目体量最大的部分，统一遵循“**控件库（components）↔ 控件使用者（main_window）**”的分层：`components.py` 提供原子控件，`main_window.py` 组装并接业务。本节按模块逐一说明。

### 8.1 themes.py — 设计令牌与主题切换

`themes.py` 是整套 UI 的**视觉单一事实源**，分两部分：

**几何常量（int/float，供 Python 代码直接读取，如 `setFixedHeight`）：**

| 常量 | 值 | 用途 |
|------|----|------|
| `CONTROL_HEIGHT` | 40 | 输入框/次要按钮/下拉框统一高度 |
| `CONTROL_PRIMARY_HEIGHT` | 48 | 主操作按钮(primary)更高，突出主次层级 |
| `COMBO_HEIGHT` | 40 | 下拉框与输入框同高 |
| `THEME_TOGGLE_SIZE` | 34 | 右上角日/月切换器边长 |
| `THEME_TOGGLE_MARGIN` | 8 | 切换器距右上角留白 |
| `THEME_TOGGLE_GAP` | 8 | 切换器投影与计数药丸的间隔 |
| `THEME_TOGGLE_AVOID` | 42 | TaskWorkspacePanel header 右侧避让宽度 |
| `ICON_STROKE` | 1.85 | 图标线宽，全仓统一 |

**`THEMES` 字典（Light / Dark 两套设计令牌）：**

每个主题包含 50+ 个令牌，按用途分组：

- **macOS 原生材质**：`macos_material`（如 `NSVisualEffectMaterialUnderWindowBackground`）、`native_window_bg`。
- **窗口/表面**：`bg`（渐变）、`bg_vibrancy`、`surface`、`sidebar`、`sidebar_hover`、`sidebar_active`、`panel`、`panel_elevated`、`card_bg`、`card_bg_hover` 等。
- **玻璃别名（供自绘控件）**：`glass_bg`、`glass_bg_strong`、`glass_border`、`glass_border_subtle`、`glass_shadow`、`inner_shadow`。
- **强调色**：`accent`（Apple Blue `#007AFF`）、`accent_hover/active/light/subtle`、`accent_gradient`（自上而下渐变）。
- **状态色**：`success`、`danger`、`warning` 及其浅底。
- **文本层级**：`fg`、`fg_secondary`、`fg_tertiary`、`fg_muted` 四级灰度。
- **线条**：`border`、`border_dark`、`border_focus`、`separator`、`highlight`。
- **输入控件**：`input_bg/hover/border`。
- **排版**：`sidebar_font_size/weight`、`section_title_size` 等 QSS 用的字符串 token。

设计纪律（注释原文明确）：`THEMES` 字典里同时保留令牌的**字符串版本**（供 QSS 模板插值）与 `int/float` 几何常量（供 Python 代码直接读取），避免 `50/34/8/36` 这类“魔数”在多文件各写一份、改一处忘一处；两套主题几何取值相同，故几何不进 dict 而设为模块常量。

### 8.2 platform_fonts.py — 跨平台字体适配

- `get_system_font_family()`：
  - Windows（`win32`）→ `"Segoe UI"`
  - macOS（`darwin`）→ `"PingFang SC"`
  - 其余 → 返回安全 fallback。
- 同时提供 `get_system_font_qss()` 与 `get_monospace_font_qss()`，用于在 QSS 片段中注入正确的 `font-family`，保证中英文与等宽（用于日志/密文）在不同系统上都有合规字体。`main_window.py` 与 `splash.py` 均依赖此模块。

### 8.3 native_effects.py — macOS 原生毛玻璃

`NativeGlassController` 把 macOS 原生 `NSVisualEffectView` 封装成可选增强，失败必降级：

- `apply(theme_data)` 启用流程（层层守卫）：
  1. `sys.platform != "darwin"` → 禁用，理由 `native glass is only available on macOS`。
  2. 环境变量 `ENCRYPTION_STUDIO_DISABLE_NATIVE_GLASS=1` → 禁用（方便调试关闭）。
  3. Qt 平台插件不是 `cocoa` → 禁用。
  4. 窗口未 `isVisible()` → 禁用（NSView 尚未就绪）。
  5. 通过守卫后 `import objc` / `AppKit`，取 `ns_view = objc.objc_object(c_void_p=int(self.window.winId()))` → `ns_window` → `contentView`，创建 `NSVisualEffectView`，设 `BlendingModeBehindWindow` + `StateActive`，以 `NSWindowBelow` 层级插入到内容视图之下。
  6. `setMaterial_` 按 `_resolve_material` 选最贴近主题的材质，并兼容不同 macOS 版本（一组 fallback 名称）。
  7. 窗口 `setOpaque_(False)` + 背景 `clearColor`，让毛玻璃透出。
- **失败降级**：任何异常 → `is_active=False`、隐藏 effect_view、`_log_fallback_once()` 只写一次日志，主流程不受影响，改用 `ui/components.py` 与 `themes.py` 共同提供的 QSS 拟态玻璃。
- `is_active` / `reason` 两个字段供 `main_window` 判断是否启用 QSS 玻璃 fallback（如 `CleanStackedWidget.paintEvent` 里 `native_glass.is_active` 决定清除色用全透明还是 `bg_vibrancy`）。

### 8.4 icons.py — 纯线稿图标引擎

`icons.py` 用 `QPainter` 自绘一套 24×24 viewBox 的线性图标，避免引入图标资源文件依赖：

- `draw_icon(painter, name, rect, color, stroke_width=ICON_STROKE)`：核心绘制函数。
  - 归一化 name（`_` ↔ `-`、小写）。
  - 以目标 `rect` 居中、按 24 网格缩放，提供 `p(x,y)` / `rr(x,y,w,h)` / `line(...)` / `poly(...)` 局部坐标助手。
  - 统一 `QPen(SolidLine, RoundCap, RoundJoin)` 线性风格，不填色。
  - 支持图标族：lock/unlock、key/credential/rsa/keypair、brand-shield、doc/log/file 等，并在 `unlock`/`rsa` 上做细节区分（解密用右上倾斜钥匙柄与闭合钥匙区分；RSA 追加套环）。
- `make_icon(name, color, size)` → 返回 `QIcon`，供需要 QIcon 的场景（如托盘、窗口图标）。

> 自绘线稿的好处：零资源文件、随主题动态着色（颜色由 `themes` 令牌传入）、矢量在任何 DPI 清晰、与 macOS Sonoma/Sequoia 线性视觉一致。

### 8.5 components.py — 自定义 UI 组件库

`components.py`（约 1814 行）是项目最大的控件库，单文件囊括 24 个自定义控件，全部遵循 macOS Sonoma/Sequoia 视觉：

- **`qcolor(value, fallback, alpha)`**：把主题 token（含 `rgba(...)` QSS 字符串）转 `QColor` 的统一桥，是所有自绘控件的色彩入口。
- **容器/表面类**：
  - `CleanStackedWidget`：在每次 paint 前清除半透明残影像素；`native_glass` 激活时用全透明清除，否则用 `bg_vibrancy`，再绘制 `bg_vibrancy` 圆角玻璃底 + 细边。
  - `PageSurface`：稳定页根，放入 `CleanStackedWidget`。
  - `GlassCard` / `GlassSectionCard` / `GlassWidget`：玻璃质感卡片。
  - `ConfigPanelCard`：配置面板卡片。
- **导航类**：
  - `AnimatedSidebarButton` / `SidebarNavButton`：带动画与 hover/active 状态的侧边栏按钮。
  - `ThemeToggleButton`：右上角日/月切换器，按 `THEME_TOGGLE_*` 几何常量绘制。
  - `BrandLogoBadge`：品牌盾形徽标。
- **输入/展示类**：
  - `DropDownComboBox`：自绘下拉框，按 `COMBO_HEIGHT` 对齐。
  - `GlassInputField`：玻璃输入框。
  - `CustomCheckBox`：自绘复选框（`test_checkbox.py` 是其独立测试）。
  - `SystemSwitchButton`：苹果风开关。
  - `IconBadge` / `KeyPairListRow`：图标徽章与密钥对列表行。
- **分区/页眉类**：
  - `SectionHeader`、`TaskWorkspacePanel`、`InspectorSection`、`ExecutionFooter`：页面分区与执行底栏。
- **交互类**：
  - `DragDropListWidget`：支持拖拽添加文件的列表，是任务队列的 UI 主体。
  - `SmoothScrollArea`：平滑滚动区。
  - `GlassProgressBar`：玻璃进度条，接收线程 `sig_progress` 驱动。
  - `ModernButton`：主/次按钮，按 `CONTROL_HEIGHT` / `CONTROL_PRIMARY_HEIGHT` 分层。

> 设计要点：组件库统一通过 `window().theme_data` 读当前主题、通过 `window().native_glass.is_active` 决定玻璃绘制方式，因此**切换主题时只需 `apply_theme()` 一次性刷新 QSS + 调 `update()`，所有自绘控件即按新令牌重绘**，无需逐控件传参。

### 8.6 splash.py — 启动动画

`IntroScreen(QSplashScreen)` 实现 500×300 圆角无边框启动动画：

- `setMask` 用 `QPainterPath.addRoundedRect` 生成圆角遮罩。
- 三个 `QPropertyAnimation`：
  - `opacity` 0→1（400ms `OutCubic`）淡入。
  - `logoScale` 0→1（600ms `OutBack`，200ms 后启动）logo 弹性缩放。
  - `progressWidth` 由 `update_progress(val,msg)` 触发，300ms `OutCubic` 平滑进度条。
- `paintEvent` 自绘：白圆角背景 → 缩放中的锁 logo → “Encryption Studio” 标题 → 加载文案 → 200px 进度条（灰底 + Apple Blue 填充）。
- `main.py` 通过 `update_progress(i*2, msg)` 驱动；`splash.finish(window)` 在主窗口显示后自动收尾。

### 8.7 utils.py — 跨平台工具函数

三个无副作用工具，被 `main_window.py` 与工作线程高频调用：

- **`ensure_long_path(path)`**：Windows 上把绝对路径加 `\\?\` 前缀，绕过 260 字符路径长度限制（防“路径过长”错误）；非 Windows 原样返回。这是处理深层目录/很中文长文件名加密的关键护栏。
- **`format_size(size_bytes)`**：B/KB/MB/GB/TB 自适应单位，保留两位小数，0 字节特判 `0 B`。
- **`get_drive_root(path)`**：沿父目录向上找到挂载点（`os.path.ismount`），用于 SSD 加速时把临时暂存区放到目标所在驱动器根，避免跨盘拷贝。

---

## 9. 主窗口 ui/main_window.py

本文件约 2692 行，是项目体量最大、也最关键的聚合点：包含**主窗口 + 两个后台批量线程**。所有耗时加解密都在此被调度到后台线程，主线程只渲染。

### 9.1 模块整体结构

文件顶层定义（按实际出现顺序）：

1. **常量与辅助函数**：`ENC_PREFIX = "ENC_DIR_"`、`encrypt_dir_name_str()` / `decrypt_dir_name_str()`、`task_wrapper()` / `run_in_subprocess()`。
2. **`class BatchWorkerThread(QThread)`**：老系统批量加密线程（进程池/线程池双模式 + SSD 加速）。
3. **`class RSABatchWorkerThread(QThread)`**：新系统 RSA 批量加密线程（单线程串行 + 暂停/停止）。
4. **`class MainWindow(QMainWindow)`**：主窗口。
5. 文件末尾一个 `if __name__ == "__main__"` 块，便于单独调试主窗口。

### 9.2 辅助函数与目录名加密

- **`encrypt_dir_name_str(dir_name)`**：若已带 `ENC_DIR_` 前缀则原样返回；否则 `base64.urlsafe_b64encode(dir_name.encode()).decode()` 后加前缀。用于 `keep_structure + encrypt_dirname` 时把目录结构里的各级目录名原地混淆，解密时识别前缀还原。
- **`decrypt_dir_name_str(dir_name)`**：识别 `ENC_DIR_` 前缀作 base64 解码还原，异常或无前缀则原样返回（幂等、不抛错）。
- **`task_wrapper(file_path, target_full_path, key_bytes, is_enc, enc_name, queue, stop_event, pause_event)`**：子进程/子线程内的单文件任务包装器，封装 `FileCipherEngine().process_file_direct(...)`，并通过 `Queue` 回传进度、通过 `Event` 接收停止/暂停，返回 `(file_path, success, msg, out_path)`。
- **`run_in_subprocess(...)`**：进程池入口的顶层函数（必须可 pickle 的模块级函数，故定义在类外），内含 `MPController`（提供 `is_stop_requested()` / `wait_if_paused()`，桥接 multiprocessing.Event 到 `FileCipherEngine` 期望的 controller 接口）。

> 目录名加密用 Base64-URL 而非真加密，是“结构混淆”而非保密——目的是让加密后的目录树看不出原始语义，但保持可逆与文件系统安全字符集；真正的文件内容与文件名才是 AES 加密的对象。

### 9.3 BatchWorkerThread — 老系统批量线程

继承 `QThread`，三条信号（线程安全通信回主线程）：

- `sig_progress(str, int)`：进度文案 + 百分比。
- `sig_log(str)`：日志文本。
- `sig_finished(dict)`：完成时回 `{success:[...], fail:[...]}`。

**`__init__` 参数**：`files, key, is_encrypt, encrypt_filename=False, custom_out_dir=None, keep_structure=False, encrypt_dirname=False, use_ssd=False, ssd_dir=None`。

**`_init_ipc()` 双模式 IPC：**

- 首选 `multiprocessing.Manager()` 创建共享 `Queue` + `Event`（stop/pause），用 `ProcessPoolExecutor`（进程池，绕开 GIL，吃满多核）。
- 失败（如 macOS 某些环境 samaphore/signal 限制）→ 降级为 `ThreadPoolExecutor` + `threading.Event`，并记录 `_ipc_init_error`经 `sig_log` 告知用户。
- `pause_event.set()` 初始为非暂停态。

**`run()` 执行流程（核心）：**

1. **密钥派生**：`key_bytes = hashlib.sha256(self.key.encode()).digest()`（老系统口令 → 32 字节 AES 密钥）。
2. **任务扫描**：遍历 `self.files`，`ensure_long_path` 后 `os.path.exists/isfile/getsize` 校验，累计 `total_bytes`、构建 `valid_files`、`processed_bytes_map`；不存在/非文件计入 `fail`。
3. **公共基目录**：`keep_structure` 时 `os.path.commonpath(files)` 求公共祖先（文件则取其目录），失败静默跳过，用于解密后还原相对结构。
4. **SSD 加速准备**（若 `use_ssd and ssd_dir`）：
   - `get_drive_root(ssd_dir)` 取目标盘根，`_SSD_ENCRYPT_STAGE_TEMP` 为暂存区，`ensure_long_path`。
   - `shutil.disk_usage` 校验空闲 ≥ `total_bytes*1.2`，不足则禁用 SSD 并告警；足够则清旧暂存区、`makedirs`、`working_root_base = 暂存区`。
   - SSD 探测异常 → 禁用并继续。
5. **并发度**：`max_workers = min(cpu_count, len(valid_files))`；启用 SSD 时 `max(max_workers, 4)` 保证暂存区并发回写不饿死。
6. **分发**：`with executor_class(max_workers) as executor` 逐文件提交 `run_in_subprocess`，按 SSD/自定义输出/原地决定每个文件 `current_base`，按 `keep_structure` 拼接 `rel_path_struct`，加密路径或加密目录名处理，最终目标路径 `ensure_long_path`。
7. **进度巡检**：定频从 `Queue` 取进度更新 `sig_progress`，直到所有 future 完成。
8. **收尾**：收集 success/fail、若启用 SSD 且未停止则把暂存区成果移回 `custom_out`、清理暂存区、`_shutdown_ipc()`、`sig_finished`。

**控制**：`pause()` / `resume()` / `stop()` 操控共享 Event；`_is_running` 状态位；`stop()` 后半成品由各子任务的 `_cleanup_partial_output` 清理。

### 9.4 RSABatchWorkerThread — 新系统批量线程

新系统（RSA 混合）的批量线程，结构与老系统相似但**串行处理**（RSA 操作较重且需私钥上下文）：

- 同样 `sig_progress/sig_log/sig_finished` 三信号。
- `__init__` 关键参数额外含 `key_path`（公钥/私钥路径）与 `key_password`（私钥口令）。
- `run()` 流程：
  1. 扫描校验文件、累计 `total_bytes`。
  2. 逐文件 `for index, file_path`：
     - `_stop_event` / `_wait_if_paused()` 检查暂停停止。
     - 决定输出目录（`custom_out` 或文件同目录），`os.makedirs(..., exist_ok=True)`。
     - 加密：`{uuid.uuid4().hex[:12]}.enc`（`encrypt_filename`）或 `{fname}.enc`。
     - 解密：`fname.replace(".enc","")`，但结果路径以 `RSAFileCipher` 返回的 `actual_out_path` 为准（强制恢复原始名）。
     - `progress_callback` 把当前字节映射为全局百分比，停止时抛 `InterruptedError`。
     - 调 `RSAFileCipher.encrypt_file/decrypt_file`，按返回 success/fail 归类并经 `sig_log` 报告。
  3. 完成后 `sig_progress(\"已完成/已终止\",100)` + `sig_finished(results)`。
- `is_stop_requested` / `wait_if_paused` 线程内自旋等待，停止响应延迟 ≤ 一个文件的处理时间。

> 老系统并发度优先（进程池吃多核），新系统串行优先（RSA 上下文重、私钥需口令、避免并发改写）——这是两种加密体系在工程取舍上的不同体现。

### 9.5 MainWindow — 主窗口架构

`MainWindow(QMainWindow)`，`setFixedSize(1200, 850)`，无边框窗口。

**`__init__`（关键状态初始化）：**

- `theme_names = list(THEMES.keys())`；`current_theme_idx = self._system_scheme_theme_idx()` —— **启动即跟随系统明暗主题**（系统 Dark→Dark，Light/Unknown→Light）。
- `theme_data = THEMES[...]`；若干业务状态：`custom_enc_path/dec_path/ssd_path`、`last_out_dir`、`is_paused`、`worker`、`all_buttons`、`sidebar_btns`、`use_new_system=False`（默认老系统）、`native_glass = NativeGlassController(self)`。
- `_init_tray()` 建系统托盘 → `_init_ui()` 组装界面 → `apply_theme()` 应用一次主题。
- 连接 `QGuiApplication.styleHints().colorSchemeChanged` 到 `_on_system_scheme_changed`：**系统明暗变化时自动纠正回系统主题**（覆盖用户手动预览），无信号时静默降级。

**主要 UI 组装方法（`_init_ui` 调用）：**

| 方法 | 职责 |
|------|------|
| `_create_common_layout` | 构造加解密页共性布局（文件列表、配置面板、进度、操作按钮） |
| `_init_page_encrypt` | 加密页（含老系统口令 / 新系统密钥选择、文件名混淆、SSD 等勾选项） |
| `_init_page_decrypt` | 解密页 |
| `_init_page_key_management` | RSA 密钥管理页（生成/导入/列表/删除） |
| `_init_page_log` | 系统日志审计页（实时显示日志） |
| `create_config_section` | 通用可折叠配置分区构建器 |
| `_position_theme_toggle` | 把 `ThemeToggleButton` 定位到右上角并避让计数药丸 |

**动作槽（用户交互 → 业务）：**

- 文件操作：`action_add_file` / `action_add_folder` / `action_remove_file` / `action_open_folder`。
- 目录选择：`action_select_dir` / `action_clear_dir` / `action_select_ssd` / `action_clear_ssd`。
- 任务控制：`action_toggle_pause` / `action_stop_task` / `reset_ui_state` / `_set_task_setup_enabled`。
- 系统切换：`action_switch_system`（老↔新，鉴权后切换密钥管理可见性）、`_start_old_system_process` / `_start_new_system_process`。
- RSA 密钥：`action_generate_keypair` / `action_import_keypair` / `action_refresh_keys` / `refresh_key_combos` / `action_delete_key` / `_select_key_file` / `_do_import_keypair`。
- 主题：`apply_theme` / `_toggle_theme_preview` / `on_theme_selected` / `_on_system_scheme_changed`。
- 托盘/窗口：`_init_tray` / `on_tray_activated` / `show_window` / `quit_app` / `closeEvent` / `showEvent` / `resizeEvent` / `_manual_move`（无边框窗口靠此支持拖动）。
- 信号接收：`update_progress`（接 `sig_progress`）、`append_log`（接 `sig_log`）、`on_finished`（接 `sig_finished`）、`update_queue_count`。
- 结构选项：`on_struct_toggled` / `on_struct_toggled_dec`（保持目录结构勾选联动）。
- 校验：`check_constraints`（开始任务前校验口令/密钥/文件非空等约束）。

### 9.6 页面与视图体系

`_init_ui` 用一个 `QStackedWidget`（实为 `CleanStackedWidget`）承载多个页面，侧边栏 `SidebarNavButton` 切换 `switch_page`：

- **加密页（老 / 新两态）**：文件拖放列表 → 配置区（老系统：口令、文件名混淆、保持结构、目录名加密、SSD 加速；新系统：公钥选择、文件名混淆）→ 操作按钮（开始/暂停/停止/打开目录）→ 进度条 + 日志。`_start_old_system_process` / `_start_new_system_process` 分别构造对应 `BatchWorkerThread` / `RSABatchWorkerThread` 并启动。
- **解密页**：镜像加密页，配置区改为口令（老）/私钥+口令（新），`on_struct_toggled_dec` 控制目录结构还原。
- **密钥管理页**（仅新系统可见）：`_init_page_key_management` 构建生成区（密钥名 + 口令 + 生成按钮）、导入区（同时选公钥/私钥 PEM）、密钥对列表（`key_list`）+ 刷新/删除。
- **日志页**：`_init_page_log` 提供实时系统日志审计，`append_log` 把 `sig_log` 文本追加显示，同时 `core.logger` 也持久化到 `Logs/` 文件双写。

`action_switch_system` 在切换时刷新密钥管理页可见性、密钥下拉项、主标题与按钮文案，并由 `refresh_key_combos` 同步加/解密页里的 RSA 密钥下拉。

### 9.7 主题系统与 macOS 毛玻璃

- **切换主题**：`apply_theme()` 是唯一入口——用 `theme_data` 渲染整套 QSS（包括各控件 stylesheet），遍历 `all_buttons` / `sidebar_btns` 刷新自绘控件，令 `CleanStackedWidget` 等按 `native_glass.is_active` 决定玻璃绘制。
- **跟随系统**：`_system_scheme_theme_idx()` 读 `QGuiApplication.styleHints().colorScheme()` 决定初始主题；`_on_system_scheme_changed` 在系统明暗变化时重新 `apply_theme()` 并纠正当前主题索引（覆盖手动预览）。
- **手动预览**：`_toggle_theme_preview` / `on_theme_selected` 在用户点击 `ThemeToggleButton` 或主题列表时即时预览，但不持久化（系统再次变化时被纠正回系统主题）。
- **macOS 毛玻璃**：`showEvent` 里（窗口可见后）调用 `native_glass.apply(theme_data)` 启用原生 vibrancy；非 macOS 或失败时 `_logged_reason_once` 写一次日志，UI 自动落在 QSS 拟态玻璃。`resizeEvent` 同步重设毛玻璃 `effect_view` 尺寸。

> 主题与材质全部由 `themes.py` 的令牌与 `native_effects.py` 的控制器驱动，切换无须改控件代码——这是组件库与令牌解耦的收益。

### 9.8 系统托盘与生命周期

- `_init_tray()` 创建 `QSystemTrayIcon`，菜单含「显示窗口」「退出」等项；`on_tray_activated` 处理双击托盘恢复窗口；`show_window` 把窗口从最小化还原并置顶。
- `closeEvent` 拦截关闭：最小化到托盘而非退出（典型企业安全工具行为）；`quit_app` 才是真正退出。
- `quit_app` 会先确认是否有未完成 `worker`，必要时 `worker.stop()` + 等待，再安全退出，避免后台线程被强行终止留下半成品文件。

### 9.9 RSA 密钥管理界面

`_init_page_key_management` 构建：

- **生成密钥对**：`action_generate_keypair` 弹框收集密钥名+口令 → 调 `RSAKeyManager.generate_key_pair(password, key_name)` → 落盘到 `DIRS["KEYS"]/{name}_public.pem` 与 `{name}_private.pem` → `action_refresh_keys` 刷新列表与下拉。
- **导入密钥对**：`action_import_keypair` 弹框同时选公钥/私钥 PEM → `_do_import_keypair` 校验存在性、覆盖确认、`shutil.copy2` 复制到 `Keys/` → 刷新。
- **列表与删除**：`key_list` 显示密钥对；`action_delete_key` 取 `currentItem().data(UserRole)` 得 key_name → **二次确认弹框**（删除是高风险操作，与 AGENTS.md “删除需二次审核”一致）→ 删除 `_public.pem`/`_private.pem` → 日志 + 刷新。
- **下拉联动**：`refresh_key_combos` 同步加/解密页的 RSA 密钥下拉项，保证生成/导入后立即可用。

### 9.10 信号槽全链路

以老系统加密为例的完整链路（新系统同理，线程类换成 `RSABatchWorkerThread`）：

```
用户点「开始」
  → _start_old_system_process / _start_new_system_process
     → check_constraints 校验
     → 构造 BatchWorkerThread(files, key, is_encrypt, encrypt_filename,
                              custom_out_dir, keep_structure, encrypt_dirname,
                              use_ssd, ssd_dir)
     → worker.sig_progress.connect(self.update_progress)
     → worker.sig_log.connect(self.append_log)
     → worker.sig_finished.connect(self.on_finished)
     → worker.start()                         # QThread 后台执行 run()
        └─ 进程池/线程池分发 → task_wrapper → FileCipherEngine.process_file_direct
           └─ callback → 经 Queue → sig_progress.emit
              └─ sig_log.emit
     主线程依据不卡顿，事件循环正常绘制

[主线程槽]
  update_progress(text, pct) → GlassProgressBar + 文案
  append_log(text)          → 日志页 + 控制台 + 文件双写
  on_finished({success,fail})→ 汇总弹框 + 刷新 UI + 清理已启用状态

[用户暂停/停止]
  action_toggle_pause → worker.pause()/resume()
  action_stop_task    → worker.stop() → 共享 Event → 子任务边界检测 → InterruptedError → 清半成品
```

> 这条链路是项目“主线程零阻塞”承诺的工程兑现：每次加解密经线程 → 信号 → 槽，主线程只在槽内做轻量 UI 更新，耗时全在后台。

---

## 10. 加密文件二进制格式规范

**老系统（AES-256-CBC，`FileCipherEngine`）文件格式：**

```
[ IV(16) ][ NameLen(4, big-end uint32) ][ EncNameBytes(NameLen) ][ OriginSize(8, big-end uint64) ][ AES-CBC(PKCS7) 密文块... ]
```

- IV：16 字节，`os.urandom`。
- NameLen：加密文件名字节数（4 字节大端无符号整型）。
- EncNameBytes：原始文件名 UTF-8 后用同一 AES 密钥+同一 IV 加密的密文。
- OriginSize：原始文件字节数（8 字节大端无符号，供解密端预知/校验）。
- 密文：文件内容经 AES-256-CBC + PKCS7 填充电后分块写出。

**新系统（RSA 混合，`RSAFileCipher` + `FileFormat`）V2 文件格式：**

```
[ MAGIC "ENC2"(4) ][ VERSION(1) ][ IV_LEN(1) ][ IV ][ METADATA_LEN(4, big-end uint32) ][ METADATA(JSON, UTF-8) ][ 加密的 AES 会话密钥 ][ 加密的文件名 ][ AES-CBC 密文块... ]
```

- 魔术字 `ENC2` 用于解密时识别版本，未来可演进 V3 而不破坏旧文件。
- METADATA（JSON）携带算法、原始文件名等元数据，由 `FileFormat.pack_v2_header` / `unpack_v2_header` 统一打包解包。
- AES 会话密钥由 RSA-2048(OAEP/SHA-256) 公钥加密；解密时需私钥+口令。
- 文件名与内容均由 AES-256-CBC 加密，解密后强制恢复原始文件名。

> 两套格式的共性：**文件名都被加密进文件头**，解密端有能力无损还原原始文件名；解密时无视传入目标文件名，以头内原始名为准——这是“文件名混淆”功能的底层保障。

---

## 11. 多线程与多进程架构

项目对“开销放后台”这一原则执行得很彻底，具体分两层：

**UI 线程（主线程）：**

- 只做事件循环、布局、绘制、轻量槽函数（更新进度条/日志/状态）。
- `main.py` 启动动画里 `QThread.msleep(10)` + `app.processEvents()` 是唯一例外，仅用于启动期约 0.5 秒的加载动画，绝不出现在业务路径。

**后台工作线程（`QThread` 子类）：**

| 类 | 系统 | 并发模型 | 控制点 |
|----|------|---------|--------|
| `BatchWorkerThread` | 老系统(AES) | 进程池优先，失败降级线程池 | 进程/线程 + 共享 Queue/Event |
| `RSABatchWorkerThread` | 新系统(RSA) | 串行（单 QThread） | 线程内 Event + 自旋等待 |

**进程池 vs 线程池的取舍（`_init_ipc`）：**

- 进程池（`ProcessPoolExecutor`）：绕开 Python GIL，AES 加密 CPU 密集型可吃满多核，是 GB 级文件批量加速的关键。
- 线程池（`ThreadPoolExecutor`）：当 `multiprocessing.Manager()` 创建失败（如 macOS 某些信号/沙箱限制、或在受限环境）时降级；I/O 弱并行，但兼容性更好、资源开销更小。
- 降级时经 `sig_log` 向用户透明告知“多进程通信初始化失败，已降级为线程池模式 + 原因”。

**进程间通信：**

- 进程模式用 `multiprocessing.Manager().Queue()/Event()`（跨进程共享）传进度与停止/暂停事件。
- 线程模式用 `queue.Queue()` + `threading.Event()`。
- `_shutdown_ipc()` 关 `Manager` 时对 `BrokenPipeError/EOFError/OSError` 静默吞掉（子进程可能已结束）。

**暂停/停止语义：**

- 暂停为“**协作式**”：在文件块边界或文件边界检测 `pause_event`，当前文件处理完才真正停顿，而不是中途杀线程（避免半成品）。
- 停止同样在块/文件边界通过 `is_stop_requested()` 抛 `InterruptedError("STOP")`，触发 `_cleanup_partial_output` 删掉半成品文件，再上报“用户终止”。

> 这套设计保证：无论如何暂停/停止，磁盘上都不会留下加密了一半的损坏文件——清理逻辑与停止逻辑绑定，是安全软件的基本功。

---

## 12. SSD 加速机制详解

SSD 加速是老系统 `BatchWorkerThread` 的可选特性，针对“大文件批量加密、输出盘是慢盘（如网络盘/机械盘）”场景：

**启用条件（`run()` 内）：**

1. 用户在 UI 勾选「SSD 加速」并选择一个高速 SSD 目录（`action_select_ssd`）。
2. 处理时 `use_ssd=True` 且 `ssd_dir` 非空。

**执行步骤：**

1. `get_drive_root(ssd_dir)` 取 SSD 所在盘根目录。
2. 暂存区 `temp_stage_root = <盘根>/_SSD_ENCRYPT_STAGE_TEMP`，`ensure_long_path` 加长路径前缀。
3. `shutil.disk_usage(ssd_dir)` 校验空闲空间 ≥ `total_bytes * 1.2`（留 20% 余量）：
   - 不足 → `sig_log` 告警（显示需要/可用），禁用 SSD，`working_root_base = custom_out`（退回原地/自定义输出）。
   - 足够 → 清旧暂存区 `shutil.rmtree(ignore_errors=True)`，`makedirs`，`working_root_base = 暂存区`。
4. `max_workers = max(max_workers, 4)`：启用 SSD 时至少 4 并发，保证暂存区写入不饿死。
5. 加密产物先全部写到 SSD 暂存区（高速），全部完成且**非用户终止**时再移回 `custom_out`（慢盘），并清理暂存区。
6. 任何 SSD 探测异常 → 禁用 SSD 并以 `sig_log` 提示，继续用普通输出路径，不中断任务。

**收益与边界：**

- 收益：把“加密写”这一高吞吐步骤放在快盘，把“最终落盘”集中到末尾一次性搬运，减少对慢输出盘的随机写。
- 边界：需 SSD 空闲 ≥ 任务总量 1.2 倍；若用户中途停止则不搬运暂存区产物（避免半成品），暂存区在下次启用时被清。跨盘搬运在大文件时仍有耗时，建议输出盘让用户选高速位置。

---

## 13. 跨平台适配策略

项目在“严格跨平台”上有系统性措施，集中体现于：

**路径处理：**

- 全仓 `os.path.join / dirname / basename / commonpath / relpath / split`，`config.py` 的 `BASE_DIR` 自适应 `sys.frozen`，无硬编码斜杠。
- Windows 长路径：`ui/utils.py::ensure_long_path` 自动加 `\\?\` 前缀，解决 >260 字符路径（深层目录 + 长中文文件名）的加解密失败。
- `get_drive_root` 用 `os.path.ismount` 跨平台取盘根（Windows 盘符 / Unix 挂载点通用）。

**字体：**

- `platform_fonts.get_system_font_family` 按 `sys.platform`（`win32`/`darwin`）返回 `Segoe UI` / `PingFang SC`，等宽与 QSS 注入同理，避免中英文 fallback 难看。

**原生特效：**

- macOS：`NativeGlassController` 启用 `NSVisualEffectView`，按 macOS 版本 fallback 多套材质。
- 其余平台：QSS 拟态玻璃（`CleanStackedWidget`/`GlassCard` 等用 `bg_vibrancy` + 半透明边）。
- 环境变量 `ENCRYPTION_STUDIO_DISABLE_NATIVE_GLASS=1` 可强制关闭原生玻璃便于调试。

**图标：**

- 自绘线稿图标（`icons.py`），随主题着色、矢量于高 DPI 清晰，无资源文件跨平台顾虑。

**多进程兼容：**

- `main.py` 必须在 `QApplication` 之前调 `multiprocessing.freeze_support()`，否则 PyInstaller 打包后 Windows 多进程失效。
- 进程池失败自动降级线程池，兼顾 macOS 受限环境。

**任务栏与窗口：**

- Windows 用 `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID` 注册独立应用身份，正确显示图标与任务栏分组；非 Windows 自动跳过。
- 无边框窗口的拖动由 `_manual_move` 处理（跨平台鼠标事件），不依赖平台窗口管理器装饰。

---

## 14. 性能优化与分块策略

**智能分块（`FileCipherEngine._get_smart_chunk_size`）：**

| 文件段 | chunk | 目的 |
|--------|-------|------|
| <100MB | 1MB | 小文件细粒度，进度刷新及时 |
| <2GB | 10MB | 中等文件平衡 I/O 调用与内存 |
| ≥2GB | 64MB | 超大文件减少 syscall、最大化吞吐 |

**流式加密（无全量加载）：**

- 逐块 `f.read(chunk)` → `encryptor.update(padder.update(chunk))` → `f_out.write(...)`，**文件内容从不上驻全内存**，GB 级文件内存占用 ≈ 单块大小（1-64MB）。
- 末尾 `encryptor.update(padder.finalize()) + encryptor.finalize()` 收尾，PKCS7 填充只在收尾写入。

**多核并发：**

- 老系统进程池 `min(cpu_count, len(valid_files))`，SSD 场景下限 4，充分利用多核加密。
- 新系统串行（RSA 上下文重，私钥需口令，避免并发改写）。

**I/O 优化：**

- 长路径前缀规避 Windows 260 限制，避免大文件因路径过长失败重试。
- SSD 暂存区把高吞吐写步骤放快盘（见 §12）。
- `_cleanup_partial_output` 保证失败不留半成品，避免磁盘垃圾累积。

**进度精准：**

- 老系统按已处理字节 / 文件大小百分比；新系统按累计已处理字节 / 总字节数全局百分比（`progress_callback` 把单文件进度映射到全局）。

---

## 15. 错误处理与日志体系

**分层异常策略：**

- **核心层**：`cryptography` 的 `InvalidToken/ValueError/UnsupportedAlgorithm` 被捕获并转成 `(False, msg, ...)` 返回，绝不让异常冒泡到 UI 崩溃；`text_cipher` 解密失败统一抛 `ValueError("密码错误或密文损坏")`，不泄漏内部。
- **文件层**：`file_cipher` 捕 `InterruptedError`（用户停止）→ 清半成品 → `(False,"用户终止")`；捕 `ValueError` → 判数据损坏/填充错；其余异常进 `sys_logger.log("error")` → `(False, str(e))`。`_cleanup_partial_output` 删除失败亦写 warning，不二次抛。
- **线程层**：`BatchWorkerThread` 扫描阶段把不存在/非文件计入 `fail`；进程池初始化失败降级线程池并 `sig_log` 告知；SSD 空间不足/探测异常禁用并告知，不中断。
- **UI 层**：`check_constraints` 在开始前校验约束；`on_finished` 汇总 success/fail 弹框提示；删除密钥等高危操作二次确认。

**日志双通道单例（`core/logger.py`）：**

- 文件：`RotatingFileHandler` 10MB×5、UTF-8、时间戳到秒、含文件名:行号，路径 `DIRS["LOGS"]/Encrypt_{YYYYMMDD_HHMMSS}.log`，自动轮转不爆盘。
- 控制台：`StreamHandler(sys.stdout)`，开发期实时可见。
- `propagate=False` 防重复；模块级 `sys_logger` 单例供全仓复用。
- UI 日志页 `append_log` 同时把 `sig_log` 文本显示到界面，实现“界面 + 控制台 + 文件”三路可审计。

---

## 16. 打包与构建

**依赖文件（来源 `requirements.txt` 等实际内容）：**

- `PySide6>=6.7.0`：Qt6 GUI。
- `cryptography>=46.0.0`：AES/RSA 加密核心。
- `pyobjc-framework-Cocoa>=11.0`：macOS AppKit（原生毛玻璃）。
- `pyinstaller>=6.17.0` / `pyinstaller-hooks-contrib>=2025.10`：PyInstaller 打包。
- `cx_Freeze>=8.5.0` / `Nuitka>=2.8.9`：备选打包方案。
- `requirements-macos.txt`：macOS 专属补充依赖。
- `requirements-dev.txt`：开发期附加依赖。
- `docs/setup.md`：说明（Python≥3.10.10；`colorama` 可选控制台彩色）。

**打包规格 `EncryptionStudio.spec`（PyInstaller）：**

- 定义入口 `main.py`、图标 `fileenc.ico`、资源（assets/PNG 等）、隐式导入（`cryptography` 后端等）。
- 关键约束：`main.py` 的 `multiprocessing.freeze_support()` 必须先于 `QApplication`，否则 Windows 打包后多进程重入崩溃。

**构建产物：**

- `build/`：中间产物；`dist/`：最终可发布目录。
- `export_code.py`：把全仓源码合并为 `all_code.txt`，便于一次性查阅或外部归档（非运行必需）。

**运行命令：**

- 开发：`python main.py`
- 打包（Windows 优先）：`pyinstaller EncryptionStudio.spec`
- 产物 `dist/` 下为独立可分发目录；纯单文件 exe 也可得但项目方不推荐（注释指出可能存在 bug）。

---

## 17. 已知边界情况与风险提示

以下是基于源码与 AGENTS.md 约束整理的工程风险与建议：

- **进程池降级**：macOS 某些沙箱/信号限制下 `multiprocessing.Manager()` 可能初始化失败，会自动降级线程池，性能下降但不中断。生产环境若要保进程池，需确认目标 macOS 的 `start method` 与签名/沙箱配置。
- **跨盘 SSD 搬运**：SSD 加速把产物暂存快盘，结束时再搬回 `custom_out`（慢盘）会产生一次跨盘大文件拷贝，耗时不可忽略；若输出本就在快盘上，收益有限，建议用户据此选择是否启用。
- **SSD 空间要求**：暂存区需 ≥ 任务总量 1.2 倍空闲，空间告警即禁用并回退，不会损坏数据，但应提前告知重度用户。
- **长路径**：Windows 深层目录/超长中文名加密依赖 `ensure_long_path` 的 `\\?\` 前缀；非项目内拼接的路径（如外部直接传参）若未走该函数仍可能触发 260 限制，二次集成时需保持调用规范。
- **私密算法**：`text_cipher` 含 DES/3DES/RC4（`decrepit_algorithms`）仅用于兼容旧产物，**不应再用于新文本加密**；新文本默认走 AES + PBKDF2 派生。
- **删除安全**：AGENTS.md 规定任何删除文件操作需明确说明并经二次审核。源码中 `action_delete_key` 已二次确认密钥对删除；`_confirm_destructive_cleanup` 与「完成后物理删除源文件」选项均遵循此原则，集成或扩展删除类功能时务必保留二次确认。
- **主题持久化**：当前不持久化用户手动主题选择，系统明暗变化会纠正回系统主题；若需求要保留偏好，需加配置读写层（当前未实现）。
- **窗口固定尺寸**：`setFixedSize(1200,850)` 对超小屏（≤1280×800 旧型号）可能偏紧；macOS 毛玻璃在该尺寸下表现良好，超小屏建议放开最小尺寸约束。
- **资源缺失兜底**：图标、字体均自绘/系统派发，`main.py` 图标文件缺失也不崩溃；但 `fileenc.ico` 缺失会导致任务栏使用默认图标，打包时应纳入资源。
- **子进程可 pickle**：`BatchWorkerThread` 使用进程池，故传给子进程的对象必须是可 pickle 的（`run_in_subprocess`、`MPController` 因此定义在模块级而非实例方法内）；扩展时切勿传入闭包/不可序列化对象。

---

## 18. 快速上手

**环境要求：**

- Python ≥ 3.10（推荐 3.10.10 已验证）。
- Windows / macOS（Linux 需自行处理 PySide6 与原生特效缺失，毛玻璃将自动 QSS 降级）。

**安装依赖：**

```bash
pip install -r requirements.txt          # 通用
pip install -r requirements-macos.txt     # 仅有 Windows 时可略
```

**开发运行：**

```bash
python main.py
```

**典型操作流程（以老系统加密为例）：**

1. 启动后由启动动画进入主窗口，默认跟随系统明暗主题、默认老系统。
2. 「加密」页拖入文件/文件夹（`DragDropListWidget`），输入口令。
3. 勾选「文件名混淆」「保持目录结构」「目录名加密」「SSD 加速」（按需）。
4. 选择输出目录（或原地覆盖）、可选 SSD 暂存目录。
5. 点「开始」→ `check_constraints` → `_start_old_system_process` → 后台 `BatchWorkerThread`。
6. 进度条/日志实时更新（`sig_progress`/`sig_log`）；可「暂停/恢复」「停止」。
7. 完成 `on_finished` 弹框汇总成功/失败。

**新系统：** 顶部切换到新系统 → 「密钥管理」生成或导入 RSA 密钥对 → 「加密」选定公钥 → 开始（走 `RSABatchWorkerThread`）→ 解密时选私钥+口令。

**调试原生毛玻璃：**

- macOS 上若毛玻璃异常，设环境变量 `ENCRYPTION_STUDIO_DISABLE_NATIVE_GLASS=1` 强制 QSS 玻璃，定位是否与 `NSVisualEffectView` 有关。

**二次开发入口建议：**

- 新增强密算法：在 `core/` 新增类（建议继承 `cipher_base`），在 `main_window` 增设对应 `BatchWorkerThread` 子类与页面。
- 新增 UI 控件：放 `ui/components.py`，颜色经 `qcolor(theme_token)` 读取，几何用 `themes.py` 常量。
- 新增耗时业务：一律 `QThread` + 信号槽，禁止在主线程做 I/O 或加密。
- 任何删除文件操作：必须明确说明被删文件并经二次审核（遵循 AGENTS.md）。

---

> **文档说明**：本文件由对当前仓库源码逐文件通读后整理，所有架构结论、格式规范、流程链路均可在对应源文件中直接验证。若源码后续演进，请同步维护本文对应章节。
