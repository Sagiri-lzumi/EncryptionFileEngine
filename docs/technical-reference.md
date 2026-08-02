# Encryption Studio — 项目技术文档

> **版本**：v2.0 增强版  
> **更新日期**：2026-03-03  
> **文档性质**：开发者技术参考手册（Developer Reference）  
> **GitHub**：https://github.com/Sagiri-lzumi/sagiri

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [项目目录结构](#3-项目目录结构)
4. [模块依赖关系图](#4-模块依赖关系图)
5. [源代码文件详解](#5-源代码文件详解)
   - 5.1 [main.py — 应用入口](#51-mainpy--应用入口)
   - 5.2 [config.py — 全局配置](#52-configpy--全局配置)
   - 5.3 [core/file_cipher.py — 文件加密引擎](#53-corefilecipherpy--文件加密引擎)
   - 5.4 [core/rsa_cipher.py — RSA 混合加密](#54-corersa_cipherpy--rsa-混合加密)
   - 5.5 [core/text_cipher.py — 文本加密与兼容派生](#55-coretext_cipherpy--文本加密与兼容派生)
   - 5.6 [core/logger.py — 日志系统](#56-coreloggerpy--日志系统)
   - 5.7 [ui/splash.py — 启动动画](#57-uisplashpy--启动动画)
   - 5.8 [ui/platform_fonts.py — 跨平台字体适配](#58-uiplatform_fontspy--跨平台字体适配)
   - 5.9 [ui/main_window.py — 主窗口](#59-uimainwindowpy--主窗口)
6. [加密文件格式规范](#6-加密文件格式规范)
7. [加密与解密完整流程](#7-加密与解密完整流程)
8. [多线程与多进程架构](#8-多线程与多进程架构)
9. [UI 组件与主题系统](#9-ui-组件与主题系统)
10. [性能指标与分块策略](#10-性能指标与分块策略)
11. [错误处理与边界条件](#11-错误处理与边界条件)
12. [环境要求与安装指南](#12-环境要求与安装指南)
13. [已知问题与未来计划](#13-已知问题与未来计划)

---

## 1. 项目概述

**Encryption Studio** 是一个基于 Python 和 PySide6 开发的**本地文件安全防御系统**。项目采用完全离线架构，所有加解密运算均在用户本地完成，无任何网络上传风险。

核心设计目标：
- **安全性**：采用工业级 AES-256-CBC 加密，支持文件名混淆防止元数据泄露
- **性能**：智能分块策略 + 进程池（`ProcessPoolExecutor`），轻松处理 GB 级超大文件
- **易用性**：现代化深色 UI，拖拽添加文件，批量队列管理，一键操作
- **鲁棒性**：全程 `ensure_long_path()` 防护，支持 Windows 超长路径（>260字符）

> ⚠️ **重要声明**：本项目为完全离线版本，所有操作均发生在本地磁盘，不涉及任何云服务或网络传输。

---

## 2. 技术栈与依赖

| 依赖库 | 版本要求 | 用途 |
|--------|----------|------|
| `Python` | ≥ 3.10.10 | 运行环境 |
| `PySide6` | 最新稳定版 | GUI 框架（Qt6 绑定） |
| `cryptography` | 最新稳定版 | 文件加密核心（AES-256-CBC），`FileCipherEngine` 专用 |
| `colorama` | 可选 | 控制台日志彩色输出（安全降级，无此库也可正常运行） |


---

## 3. 项目目录结构

```
EncryptionFileEngine/
│
├── main.py                  # 🚀 应用入口，多进程支持，图标注册，启动流程编排
├── config.py                # ⚙️  全局配置：BASE_DIR 适配 + 目录定义（os.path 字符串）+ 分块策略
│
├── core/                    # 📦 核心业务逻辑层
│   ├── __init__.py          #   空文件（包标识，未导出公开 API）
│   ├── file_cipher.py       # 文件加密引擎（AES-256-CBC，约 130 行）
│   ├── rsa_cipher.py        # RSA 混合加密与密钥管理
│   ├── text_cipher.py       # 文本加密、编码和新旧密钥派生兼容
│   └── logger.py            # 全局日志系统，单例模式，带轮转（约 120 行）
│
├── ui/                      # 🎨 用户界面层
│   ├── __init__.py          #   空文件（包标识，未导出公开 API）
│   ├── splash.py            # 启动动画画面（IntroScreen，约 95 行）
│   ├── platform_fonts.py    # 跨平台字体选择工具
│   └── main_window.py       # 主窗口（5 个核心类 + 6 个工具函数，约 700 行）
│
├── docs/                    # 📚 开发者文档
│   ├── README.md            #   文档索引
│   ├── setup.md             #   环境依赖与安装说明
│   ├── technical-reference.md # 本文档（面向开发者的技术手册）
│   └── architecture-deep-dive.md # 完整深度解析
│
├── scripts/                 # 🛠️ 开发辅助脚本
│   └── export_code.py       #   代码导出工具（被 .gitignore 忽略）
│
├── tests/                   # ✅ 测试与实验脚本
│   └── test_checkbox.py     #   复选框样式测试脚本
│
├── Keys/                    # 🔑 密钥存储目录（运行时自动创建）
│
├── Logs/                    # 📋 日志文件目录（运行时自动创建）
│   └── Encrypt_YYYYMMDD_HHmmss.log  # 带秒级时间戳的日志文件
│
├── OriginalFile/            # 📂 待处理源文件存放目录（UI 默认工作区）
├── EncryptedFile/           # 🔒 加密输出目录
├── DecryptedFile/           # 🔓 解密输出目录
├── TempCache/               # ⚡ SSD 加速临时缓存目录（UI 手动指定，不在 DIRS 中）
│
├── PNG/                     # 📸 截图资源
│   ├── img.png              #   启动动画截图
│   ├── img_1.png
│   ├── img_2.png
│   └── img_3.png            #   主界面截图
│
├── fileenc.ico              # 应用程序图标
├── EncryptionStudio.spec    # PyInstaller 打包配置
├── .gitignore
├── .gitattributes
├── LICENSE
├── README.md                # 用户使用说明（面向终端用户）
└── AGENTS.md                # AI 助手协作规范
```

---

## 4. 模块依赖关系图

```
main.py
 ├── config.py  (init_directories, BASE_DIR)
 ├── ui/splash.py  (IntroScreen)
 └── ui/main_window.py  (MainWindow)
       ├── config.py  (DIRS)
       ├── core/file_cipher.py  (FileCipherEngine)  ← 依赖 cryptography
       ├── core/rsa_cipher.py  (RSAFileCipher / RSAKeyManager)
       ├── core/text_cipher.py (TextCipher)
       └── core/logger.py  (sys_logger)

core/logger.py
 └── config.py  (DIRS)
```

> **关键点**：`core/logger.py` 是被所有模块引用的基础设施，通过模块级单例 `sys_logger` 共享。

---

## 5. 源代码文件详解

### 5.1 `main.py` — 应用入口

**代码行数**：约 40 行  
**职责**：负责整个应用程序的启动编排，是所有模块的聚合点。

#### 启动流程

```
main()
 │
 ├─ 1. multiprocessing.freeze_support()
 │      └─ 保证 PyInstaller 打包后多进程正确工作（Windows 必须在 if __name__=="__main__" 前调用）
 │
 ├─ 2. ctypes 注册 AppUserModelID
 │      └─ 让 Windows 任务栏将本程序识别为独立应用（正确显示图标）
 │         myappid = 'security.fileengine.cipher.1.0'
 │         ⚠️ 用 try/except ImportError 包裹，非 Windows 环境安全跳过
 │
 ├─ 3. init_directories()
 │      └─ 调用 config.py 创建所有必要目录（Keys/Logs/OriginalFile 等）
 │
 ├─ 4. QApplication 初始化 + 设置全局图标
 │      └─ 从 BASE_DIR 加载 fileenc.ico（检查文件存在性，不会因图标丢失崩溃）
 │
 ├─ 5. IntroScreen（启动动画）展示
 │      └─ 模拟加载进度：0→100%（50 步 × 10ms = 约 500ms）
 │         前半段（i < 25）显示 "LOADING KERNEL..."
 │         后半段（i ≥ 25）显示 "STARTING UI..."
 │         每步调用 app.processEvents() 保持 UI 响应
 │
 └─ 6. MainWindow 创建并显示，splash.finish(window) 淡出过渡
```

#### 关键细节

- `QThread.msleep(10)` + `app.processEvents()` 确保启动动画在主线程正常渲染，不卡顿
- 图标加载做了 `os.path.exists` 检查，不会因图标文件丢失而崩溃
- `multiprocessing.freeze_support()` 必须在 `QApplication` 初始化之前调用，否则 PyInstaller 打包后的 Windows 多进程会反复触发入口函数
- 登录验证模块已移除，当前启动流程固定直接进入 `MainWindow`

---

### 5.2 `config.py` — 全局配置

**代码行数**：约 35 行  
**职责**：提供整个项目的路径基准和性能参数，是所有模块的共享配置源。

#### BASE_DIR 双环境适配

```python
if getattr(sys, 'frozen', False):
    # 【打包环境】PyInstaller 运行时，sys.frozen = True
    BASE_DIR = os.path.dirname(sys.executable)   # .exe 所在目录
else:
    # 【开发环境】正常 Python 运行
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # config.py 所在目录
```

> **设计意图**：无论是开发调试还是打包分发，所有数据文件（日志、密钥、加解密输出）都始终放在**可执行文件旁边**，而不是散落在系统临时目录中。

#### DIRS — 目录注册表

```python
# ⚠️ 注意：DIRS 的值是 os.path.join() 返回的 str 字符串，不是 pathlib.Path 对象
DIRS = {
    "ORIGINAL":  os.path.join(BASE_DIR, "OriginalFile"),   # 源文件工作区
    "ENCRYPTED": os.path.join(BASE_DIR, "EncryptedFile"),  # 加密输出
    "DECRYPTED": os.path.join(BASE_DIR, "DecryptedFile"),  # 解密输出
    "KEYS":      os.path.join(BASE_DIR, "Keys"),            # 密钥 & 用户数据库
    "LOGS":      os.path.join(BASE_DIR, "Logs"),            # 日志文件
    # ⚠️ 故意不定义 TEMP/SSD 目录，强制由用户在 UI 中手动指定
}
```

#### CHUNK_SIZES — 智能分块策略配置表

| 分块名 | 大小 | 适用场景 |
|--------|------|----------|
| `SMALL` | 64 KB | 配置文件、小文本（⚠️ 当前引擎未使用此档） |
| `MEDIUM` | 1 MB | 文档、图片（中小文件默认） |
| `LARGE` | 10 MB | 视频片段、安装包 |
| `HUGE` | 64 MB | 超大文件（>2GB） |

#### `init_directories()` 函数

```python
def init_directories():
    for path in DIRS.values():
        if path and not os.path.exists(path):
            os.makedirs(path)
```

> 遍历 `DIRS` 所有值，若目录不存在则创建。注意：不使用 `exist_ok=True`，而是先 `os.path.exists` 判断，行为等价但写法不同。

---

### 5.3 `core/file_cipher.py` — 文件加密引擎

**代码行数**：约 130 行  
**核心类**：`FileCipherEngine`  
**加密算法**：AES-256 CBC 模式  
**依赖**：`cryptography` 库（`cryptography.hazmat.primitives`）

#### 类方法说明

| 方法 | 描述 |
|------|------|
| `_get_smart_chunk_size(file_size)` | 根据文件大小返回最优分块大小（私有方法） |
| `process_file_direct(...)` | 核心方法，同时处理加密和解密（`is_encrypt` 参数区分） |

#### `process_file_direct` 参数详解

```python
def process_file_direct(
    self,
    file_path,        # str: 输入文件路径（调用前应已经过 ensure_long_path 处理）
    target_path,      # str: 输出目标路径（解密时文件名被忽略，强制恢复原名）
    key_bytes,        # bytes: 32字节 AES-256 密钥（由调用方 SHA-256 哈希生成）
    is_encrypt,       # bool: True=加密, False=解密
    encrypt_filename, # bool: 是否混淆文件名（仅加密时有效）
    callback,         # Callable(current, total) | None: 进度回调，频率限制 50ms
    controller        # MPController | None: 多进程控制器（暂停/停止信号）
) -> tuple[bool, str, str]
# 返回值: (是否成功, 状态消息, 实际输出文件路径)
```

#### 智能分块阈值（引擎内部实际代码）

```python
def _get_smart_chunk_size(self, file_size):
    if file_size < 100 * 1024 * 1024:    # < 100 MB
        return 1 * 1024 * 1024            # 1 MB
    elif file_size < 2 * 1024 * 1024 * 1024:  # 100 MB ~ 2 GB
        return 10 * 1024 * 1024           # 10 MB
    else:                                 # > 2 GB
        return 64 * 1024 * 1024           # 64 MB
```

#### 加密时文件名加密的实现细节

文件名加密**复用主体文件的同一个 IV**，但使用一个独立的 `Cipher` 实例：

```python
# 主体加密
iv = os.urandom(16)
cipher      = Cipher(AES(key_bytes), CBC(iv))   # 用于加密文件内容
name_cipher = Cipher(AES(key_bytes), CBC(iv))   # 用于加密文件名（复用同一 IV）

# 文件名加密过程
fname_bytes = original_filename.encode('utf-8')
name_pad    = PKCS7(128).padder()
name_enc    = name_cipher.encryptor()
enc_fname_data = name_enc.update(name_pad.update(fname_bytes)) \
               + name_enc.update(name_pad.finalize()) \
               + name_enc.finalize()
```

> **设计说明**：复用 IV 节省了头部存储空间，但这意味着"文件名密文"和"文件内容密文"共享同一 IV。由于 CBC 模式下相同 IV + 相同明文会产生相同密文，若文件名不变而内容改变，文件名密文也不变——这在实际使用中是可接受的。

---

### 5.5 `core/auth.py` — 用户认证服务

**代码行数**：约 25 行  
**核心类**：`AuthService`  
**数据存储**：`Keys/users.json`（纯 JSON 文件，路径来自 `DIRS["KEYS"]`）

#### 工作原理

```python
# 初始化：若 users.json 不存在，创建并写入默认账号
AuthService.__init__()
  └─ _init_db()
       ├─ 检查 users.json 是否存在
       ├─ 不存在：os.makedirs(Keys/, exist_ok=True)
       └─ 写入默认账号：json.dump({"admin": "123456"}, f)
```

```python
# 登录验证
AuthService.login(username, password)
  ├─ open(user_db, 'r') 读取 users.json
  ├─ 检查 username in users AND users[username] == password  ← 明文字符串比较！
  ├─ 成功：sys_logger.log("用户 {username} 登录成功")，返回 True
  ├─ 失败：sys_logger.log("用户 {username} 登录失败", "warning")，返回 False
  └─ 异常：sys_logger.log("鉴权数据库读取失败: {e}", "error")，返回 False
```

#### ⚠️ 已知安全缺陷

1. **密码明文存储**：`users.json` 中密码为纯文本，任何人获取该文件即可读取所有密码
2. **明文字符串比较**：`users[username] == password` 存在时序攻击风险，应使用 `hmac.compare_digest()`
3. **无锁定机制**：不限制暴力破解尝试次数
4. **未集成到主流程**：`main.py` 当前直接创建 `MainWindow`，完全跳过登录验证

> **建议改进**：使用 `bcrypt` 或 `argon2-cffi` 对密码进行哈希存储，并使用 `hmac.compare_digest()` 进行安全比较。

---

### 5.6 `core/logger.py` — 日志系统

**代码行数**：约 120 行  
**核心类**：`LoggerService`（单例）、`LogFormatter`（自定义格式化器）  
**全局单例**：`sys_logger = LoggerService()`（模块级导出，所有模块 `from core.logger import sys_logger` 使用）

#### 单例模式实现

```python
class LoggerService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggerService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:   # 防止重复初始化
            return
        self.logger = logging.getLogger("EncryptionEngineCore")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False   # 防止日志传播到根 Logger（避免重复输出）
        self.handlers_setup = False
        self._initialized = True
```

#### Handler 懒加载机制

`_setup_handlers()` 不在 `__init__` 中调用，而是在第一次调用 `log()` 时触发：

```python
def log(self, message, level="info"):
    if not self.handlers_setup:
        self._setup_handlers()   # 懒加载：第一次调用时才初始化文件 Handler
    ...
```

**设计原因**：确保 `init_directories()` 先于日志目录访问执行，避免在 `DIRS["LOGS"]` 目录不存在时就尝试创建日志文件。

#### 日志文件 Handler 配置

```python
# Handler A：文件（带轮转）
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 单文件最大 10MB
    backupCount=5,               # 最多保留 5 个备份切片
    encoding='utf-8',
    delay=False                  # 立即创建文件，早暴露权限问题
)

# Handler B：控制台（尝试使用 colorama 颜色）
console_handler = logging.StreamHandler(sys.stdout)
```

每次程序启动生成新日志文件（秒级时间戳），`RotatingFileHandler` 主要防止**单次运行日志超过 10MB**。

#### 日志文件命名规则

```
Logs/Encrypt_20260106_205922.log
              │        │
              │        └─ 时分秒（程序启动时刻）
              └─────────── 年月日
```

#### 日志格式示例

```
2026-01-06 20:59:22.135 | MainProcess:MainThread | INFO     | file_cipher.py:45 | 日志系统初始化完成。日志路径: C:\...\Logs\Encrypt_20260106_205922.log
```

格式字段说明：

| 字段 | 示例 | 说明 |
|------|------|------|
| 时间 | `2026-01-06 20:59:22.135` | 毫秒精度（`%(msecs)03d`） |
| 进程:线程 | `MainProcess:MainThread` | 多进程调试必备，子进程会显示不同进程名 |
| 级别 | `INFO    ` | `%-8s` 固定宽度对齐 |
| 位置 | `file_cipher.py:45` | 使用 `stacklevel=2` 显示真实调用位置（非 logger.py 内部行号） |
| 消息 | `...` | 日志正文 |

#### `stacklevel` 兼容性处理

```python
# stacklevel 参数在 Python 3.8 才引入
if sys.version_info >= (3, 8):
    self.logger.log(log_level, message, stacklevel=2)
else:
    self.logger.log(log_level, message)  # 旧版本降级，位置信息显示为 logger.py 内部
```

#### colorama 安全降级

```python
try:
    import colorama
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:   # 空字符串占位类，防止 AttributeError
        BLUE = GREEN = YELLOW = RED = WHITE = CYAN = ""
    class Style:
        BRIGHT = RESET_ALL = ""
```

`LogFormatter` 中 `use_color = use_color and HAS_COLOR`，文件 Handler 强制 `use_color=False`，控制台 Handler 尝试 `use_color=True`。

#### 日志级别映射

```python
log(message, level="info")   # 默认 INFO
# level 可选值: "debug" / "info" / "warning" / "error" / "critical"
```

---

### 5.7 `ui/splash.py` — 启动动画

**代码行数**：约 95 行  
**核心类**：`IntroScreen`（继承 `QSplashScreen`）  
**尺寸**：500 × 320 像素，`Qt.FramelessWindowHint` 无边框，`Qt.WA_TranslucentBackground` 背景透明

#### 动画状态变量

```python
self.angle_fast = 0          # 外圈弧线当前角度（每帧 +12°）
self.angle_slow = 0          # 内圈弧线当前角度（每帧 -5°，反向）
self.pulse_scale = 1.0       # 中心核心缩放比（0.95 ~ 1.05 之间振荡）
self.pulse_direction = 0.02  # 呼吸方向（到边界时取反）
```

#### 动画组件详解

所有视觉元素由 `paintEvent()` 中的 `QPainter` 完全自绘，无图片资源依赖：

| 组件 | 技术实现 | 动画参数 |
|------|---------|---------|
| **背景** | `QRadialGradient(cx, cy, w*0.8)`，`#1a1b20` → `#090a0c` | 静态 |
| **中心能量核心** | `QRadialGradient(0, 0, 20)`，白→青→透明，椭圆半径 20px | 呼吸缩放（0.95~1.05，步长 0.02） |
| **外圈快速旋转弧** | `QConicalGradient`，青色（`#00e5ff`），270° 弧，线宽 6px | 每帧旋转 +12° |
| **外圈发光晕** | 单色青色半透明（alpha=30），12px 线宽 | 与外圈同步 |
| **内圈慢速反转弧** | `QConicalGradient`，红色（`#ff0055`），220° 弧，线宽 4px | 每帧旋转 -5°（反向） |
| **标题文字** | `QFont("Segoe UI", 22, Bold)` | 双层：青色半透明（发光）+ 白色前景 |
| **状态文字** | `QFont("Consolas", 9)`，青色 | 随 `update_progress()` 更新 |
| **百分比文字** | 灰色（`#666666`），右对齐 | 与状态文字同行 |
| **进度条背景** | 深色（`#222222`），3px 高，圆角 1.5px | 静态 |
| **进度条前景** | `QLinearGradient`，青色→红色渐变 | 随进度延伸 |

#### 定时器与帧率

```python
self.timer = QTimer(self)
self.timer.timeout.connect(self.animate)
self.timer.start(16)   # 16ms ≈ 62.5 FPS（理论值，受 Qt 事件循环影响实际略低）
```

#### 进度接口

```python
def update_progress(self, val: int, msg: str):
    self.progress = val                      # 0~100
    self.loading_text = f">_{msg.upper()}"   # 格式化为大写，加 ">_" 前缀
    self.update()                            # 触发 Qt 重绘
```

#### 进度条绘制坐标计算

```python
bar_w = (w - 80) * (self.progress / 100.0)   # 可用宽度 = 总宽 500 - 左右各 40px
# 左起点: x=40, 右终点: x=460, 总可用宽度: 420px
bar_fg = QRectF(40, h - 25, bar_w, 3)
```

---

### 5.8 `ui/login.py` — 登录对话框

**状态**：⚠️ **已实现但未集成到主流程中**

`LoginDialog` 类继承 `QDialog`，包含用户名/密码输入框和登录按钮，调用 `AuthService.login()` 进行验证。当前 `main.py` 直接创建 `MainWindow`，**跳过了登录验证步骤**，该模块处于待集成状态。

**集成方式**（参考）：

```python
# main.py 中应在 MainWindow 之前插入：
from ui.login import LoginDialog
login = LoginDialog()
if login.exec() != QDialog.Accepted:
    sys.exit(0)   # 登录失败则退出
```

---

### 5.9 `ui/main_window.py` — 主窗口

**代码行数**：约 700 行  
**顶层工具函数**：6 个  
**核心类**：5 个

#### 顶层工具函数

| 函数名 | 实现说明 |
|--------|---------|
| `ensure_long_path(path)` | Windows 长路径支持：为绝对路径添加 `\\?\` 前缀，解锁 32767 字符限制。非 Windows 系统原样返回。内部先调用 `os.path.abspath()` 自动将 `/` 转换为 `\` |
| `format_size(size_bytes)` | 字节数格式化为人类可读（B/KB/MB/GB/TB），循环除以 1024 |
| `get_drive_root(path)` | 获取路径所在的磁盘根目录，通过循环 `os.path.dirname` + `os.path.ismount` 检测挂载点 |
| `encrypt_dir_name_str(dir_name)` | 对目录名进行 **Base64 URL Safe 编码**（非加密！）并加 `ENC_DIR_` 前缀，幂等（已编码则跳过） |
| `decrypt_dir_name_str(dir_name)` | 检测 `ENC_DIR_` 前缀，还原 Base64 URL Safe 编码的目录名 |
| `task_wrapper(...)` | 多进程任务包装函数，在子进程中构建 `MPController`、`FileCipherEngine`，执行单文件加解密，并通过 `multiprocessing.Queue` 汇报进度 |

> **注意**：`encrypt_dir_name_str` 使用的是 `base64.urlsafe_b64encode()`，**这是编码而非加密**，任何人都可以解码还原目录名。如需真正隐藏目录名，需使用 AES 加密。

#### `ensure_long_path` 的调用链

该函数在整个 `BatchWorkerThread` 生命周期中被密集调用，是 Windows WinError 123/206 的核心修复点：

```
BatchWorkerThread.run()
 ├─ 扫描文件时：ensure_long_path(f) → os.path.exists / os.path.getsize
 ├─ SSD 暂存区：ensure_long_path(temp_stage_root)
 └─ SSD 回写时：ensure_long_path(src) / ensure_long_path(dst)

task_wrapper()
 ├─ ensure_long_path(file_path)   → 传给 FileCipherEngine
 └─ ensure_long_path(target_path) → 传给 FileCipherEngine

_manual_move()
 ├─ ensure_long_path(src)
 └─ ensure_long_path(dst)
```

#### `task_wrapper` — 进程间通信协议

```python
# 子进程 → 主线程 Queue 消息格式
queue.put(("START",    file_path, file_size))           # 任务开始，携带文件大小
queue.put(("PROGRESS", file_path, current, total))      # 进度更新（限速：50ms 间隔）
# 函数直接 return 而非 queue 发送完成消息，由 Future.result() 获取
return (file_path, success, msg, out_path)              # 通过 ProcessPoolExecutor.submit().result() 获取
```

#### 进度回调限速机制

```python
last_update = 0

def mp_callback(current, total):
    nonlocal last_update
    now = time.time()
    if now - last_update > 0.05 or current == total:   # 50ms 限速，最后一次强制发送
        queue.put(("PROGRESS", file_path, current, total))
        last_update = now
```

#### 类一览

| 类名 | 父类 | 职责 |
|------|------|------|
| `AnimatedSidebarButton` | `QPushButton` | 带 `QPropertyAnimation` 悬停动画的侧边栏导航按钮 |
| `ModernButton` | `QPushButton` | 统一风格的功能按钮，`color_type` 控制语义（normal/primary/danger） |
| `DragDropListWidget` | `QListWidget` | 支持拖拽导入文件/文件夹（递归展开）的列表控件，空状态时显示占位提示 |
| `BatchWorkerThread` | `QThread` | 多进程批量处理任务的工作线程，管理 `ProcessPoolExecutor` 生命周期 |
| `MainWindow` | `QMainWindow` | 主窗口，组合所有页面和功能，实现严格的 UI 约束逻辑 |

#### `MainWindow` 页面结构

```
MainWindow (QMainWindow, 1280×800, 最小 1100×650)
├── 左侧边栏 (QFrame#Sidebar, 固定宽 240px)
│   ├── 标题：🛡️ 安全引擎
│   ├── 🔒 加密终端 (AnimatedSidebarButton) → switch_page(0)
│   ├── 🔓 解密终端 (AnimatedSidebarButton) → switch_page(1)
│   ├── 📜 日志审计 (AnimatedSidebarButton) → switch_page(2)
│   └── [底部] 主题切换按钮 (ModernButton)
└── 右侧内容区 (QStackedWidget)
    ├── page_encrypt (index=0)   加密操作页 ─┐
    ├── page_decrypt (index=1)   解密操作页 ─┤─ 共用 _create_common_layout()
    └── page_log     (index=2)   实时日志监控页
```

#### `_create_common_layout` 布局结构

加密页和解密页共用同一个布局函数，返回 `(page, refs)` 元组：

```
page (QWidget)
└── QVBoxLayout
    └── QSplitter (水平，比例 6:4)
        ├── 左侧 QFrame#ContentPanel
        │   ├── "📄 待处理文件队列"（标题）
        │   ├── DragDropListWidget（文件列表）
        │   └── 按钮栏：➕ 添加文件 | ➕ 添加目录 | ➖ 移除选中 | 🗑️ 清空
        └── 右侧 QFrame#ContentPanel (宽度 400~500px)
            ├── "⚙️ 任务配置"（标题）
            ├── GroupBox "安全凭证"
            │   └── QLineEdit (Password 模式)
            ├── GroupBox "输出路径"
            │   ├── QLineEdit + "..." 按钮
            │   ├── QCheckBox "保留目录结构" (默认禁用，选路径后启用)
            │   └── QCheckBox "加密/解密文件夹名" (默认禁用，勾选保留结构后启用)
            ├── GroupBox "高级策略"
            │   ├── QLineEdit + "选择缓存" 按钮
            │   ├── QCheckBox "启用 SSD 加速" (默认禁用，选缓存路径后启用)
            │   ├── QCheckBox "混淆文件名" (仅加密页，默认勾选)
            │   └── QCheckBox "完成后粉碎源文件" / "解密后移除加密包"
            ├── QLabel "就绪" (状态文字)
            ├── QProgressBar (高度 6px，无文字，仅颜色块)
            └── QStackedWidget (高度 50px，3个状态页)
                ├── [0] 开始按钮
                ├── [1] 挂起 + 终止 按钮
                └── [2] 打开目录 + 返回 按钮
```

#### UI 约束逻辑（`check_constraints()`）

这是一套严格的级联控件启用/禁用逻辑，确保选项之间的依赖关系正确：

```
check_constraints() 触发时机：
  - 添加/移除文件
  - 选择输出目录
  - 选择 SSD 目录
  - 文件拖拽完成

级联规则（加密端，解密端对称）：
  ┌─────────────────────────────────────────────────────────────┐
  │ custom_enc_path 已设置？                                      │
  │   是 → chk_struct.setEnabled(True)                          │
  │   否 → chk_struct.setChecked(False) + setEnabled(False)     │
  │         → chk_dir_name_enc 联动禁用                          │
  └─────────────────────────────────────────────────────────────┘
  ┌─────────────────────────────────────────────────────────────┐
  │ chk_struct.isChecked()？                                     │
  │   是 → chk_dir_name_enc.setEnabled(True)                    │
  │   否 → chk_dir_name_enc.setChecked(False) + setEnabled(False)│
  └─────────────────────────────────────────────────────────────┘
  ┌─────────────────────────────────────────────────────────────┐
  │ custom_ssd_path 已设置？（加密解密共享此路径）                   │
  │   是 → enc/dec 两端的 chk_ssd.setEnabled(True)             │
  │   否 → 两端 chk_ssd.setChecked(False) + setEnabled(False)  │
  └─────────────────────────────────────────────────────────────┘
```

#### `MainWindow` 主要方法

| 方法 | 描述 |
|------|------|
| `_init_ui()` | 初始化整体布局（侧边栏 + 内容区） |
| `switch_page(index)` | 切换内容区页面，同步更新侧边栏按钮选中状态 |
| `_create_common_layout(is_encrypt)` | 创建加密/解密页通用布局，返回 `(page_widget, refs_dict)` |
| `_init_page_encrypt()` / `_init_page_decrypt()` | 调用通用布局，保存 refs 到 `self.ui_enc` / `self.ui_dec` |
| `_init_page_log()` | 初始化日志监控页（只读 `QTextEdit`，Consolas 字体）|
| `cycle_theme()` | 循环切换主题索引，调用 `apply_theme()` |
| `apply_theme()` | 生成全局 QSS 样式表，更新所有自定义控件主题 |
| `check_constraints()` | 执行 UI 约束级联逻辑（见上方详解） |
| `action_add_file(is_encrypt)` | 打开文件选择对话框（加密过滤"所有文件"，解密过滤"*.enc"） |
| `action_add_folder(is_encrypt)` | 打开文件夹选择对话框，用 `os.walk` 递归添加所有子文件 |
| `action_remove_file(lst, is_encrypt)` | 从任务列表移除选中项 |
| `action_select_dir(is_encrypt)` | 选择输出目录，更新对应端的 `custom_enc_path` / `custom_dec_path` |
| `action_select_ssd(is_encrypt)` | 选择 SSD 缓存目录（加密解密共享 `custom_ssd_path`） |
| `reset_ui_state(is_encrypt)` | 将对应端 UI 重置为"就绪"状态（进度条归零、按钮栈归 0） |
| `run_encrypt()` / `run_decrypt()` | 触发加密/解密任务（调用 `_start_process`）|
| `_start_process(is_encrypt)` | 校验参数，创建并启动 `BatchWorkerThread`，连接信号槽 |
| `update_progress(text, val)` | 接收 `sig_progress` 信号，更新对应端进度条和状态文字 |
| `append_log(text)` | 向日志页追加带时间戳的 HTML 文本，同时写入 `sys_logger` |
| `action_toggle_pause()` | 暂停/继续当前任务（切换按钮文字"挂起"/"继续"） |
| `action_stop_task()` | 强制停止（先 resume 解除暂停阻塞，再 stop） |
| `on_finished(results, is_encrypt)` | 任务完成回调，展示结果统计，执行源文件删除（若勾选） |
| `action_open_folder()` | 用 `QDesktopServices.openUrl()` 在文件管理器中打开输出目录 |

#### `_start_process` 密钥生成

```python
# 密钥在 BatchWorkerThread.run() 中生成（不在主线程）
key_bytes = hashlib.sha256(self.key.encode()).digest()   # 32字节，SHA-256 派生
```

---

## 6. 加密文件格式规范

每个加密文件（`.enc`）的二进制结构如下：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          加密文件二进制布局                               │
├──────────┬────────────┬──────────────────┬────────────┬─────────────────┤
│ IV       │ NameLen    │ EncName          │ OriginSize │ 加密数据块        │
│ 16 字节  │ 4 字节     │ N 字节           │ 8 字节     │ 变长             │
│ (随机)   │ (Big-End.) │ (AES+PKCS7加密)  │ (Big-End.) │ (AES-CBC+PKCS7) │
└──────────┴────────────┴──────────────────┴────────────┴─────────────────┘
```

#### 字段详解

| 字段 | 类型 | 大小 | 说明 |
|------|------|------|------|
| `IV` | `bytes` | 固定 16 字节 | AES-CBC 初始化向量，`os.urandom(16)` 生成，每文件唯一 |
| `NameLen` | `uint32 BE` | 固定 4 字节 | 加密后文件名的字节长度（`struct.pack('>I', ...)` 编码）|
| `EncName` | `bytes` | N 字节（由 NameLen 决定）| 用**同一个 IV 和密钥**加密的原始文件名（UTF-8 编码后 PKCS7 填充再 AES 加密）|
| `OriginSize` | `uint64 BE` | 固定 8 字节 | 原始文件的字节大小（`struct.pack('>Q', ...)` 编码，解密时当前代码跳过此字段）|
| 加密数据块 | `bytes` | 变长 | 原始文件内容经 AES-256-CBC + PKCS7 填充后的密文 |

#### 文件头大小计算

```
header_size = 16 (IV) + 4 (NameLen) + N (EncName, PKCS7 填充到 16 的倍数) + 8 (OriginSize)
data_size   = total_file_size - header_size
```

> ⚠️ `OriginSize` 字段目前在解密时被读取后**直接跳过**（`f_in.read(8)` 无赋值），未用于校验文件完整性。这是一个未来可改进的点。

#### 文件名混淆行为

当 `encrypt_filename=True` 时：
- 加密输出文件名变为：`{uuid4().hex[:12]}.enc`（例如 `a3f7c91d2b04.enc`）
- 原始文件名被 AES 加密后存入 `EncName` 字段
- 解密时**自动从头部还原原始文件名**，忽略传入的 `target_path` 文件名部分

当 `encrypt_filename=False` 时：
- 加密输出文件名为 `原始文件名.enc`（例如 `document.pdf.enc`）
- `EncName` 字段仍然写入，只是文件名信息可从外部文件名推断

---

## 7. 加密与解密完整流程

### 7.1 加密流程

```
process_file_direct(file_path, target_path, key_bytes, is_encrypt=True, ...)
│
├─ [前置检查]
│   ├─ os.path.exists(file_path) → 不存在则 return (False, "源文件不存在", "")
│   └─ os.makedirs(target_dir, exist_ok=True) → 自动创建输出目录
│
├─ [计算分块大小]
│   └─ chunk_size = _get_smart_chunk_size(os.path.getsize(file_path))
│
├─ [若 encrypt_filename=True] 生成随机输出文件名
│   └─ str(uuid4().hex)[:12] + ".enc" → 覆盖 final_out_path
│
├─ [生成加密材料]
│   ├─ iv = os.urandom(16)                              ← 随机 16 字节，每文件唯一
│   ├─ Cipher(AES(key_bytes), CBC(iv)) → 主体加密器
│   ├─ PKCS7(128).padder() → 主体填充器
│   └─ Cipher(AES(key_bytes), CBC(iv)) → 文件名加密器（复用同一 IV）
│
├─ [加密文件名（AES-CBC + PKCS7）]
│   ├─ fname_bytes = original_filename.encode('utf-8')
│   ├─ PKCS7 填充 + AES 加密
│   └─ 得到 enc_fname_data（长度是 16 的倍数）
│
├─ [写入文件头]
│   ├─ f_out.write(iv)                                  ← 16 字节
│   ├─ f_out.write(struct.pack('>I', len(enc_fname_data))) ← 4 字节
│   ├─ f_out.write(enc_fname_data)                      ← N 字节
│   └─ f_out.write(struct.pack('>Q', file_size))        ← 8 字节
│
├─ [分块加密主体（流式处理，不全量加载到内存）]
│   ├─ 循环读取 chunk_size 大小的数据块
│   │   ├─ 检查 controller.is_stop_requested() → 抛出 InterruptedError("STOP")
│   │   ├─ 检查 controller.wait_if_paused() → 暂停时阻塞
│   │   ├─ encryptor.update(padder.update(chunk)) → 流式加密
│   │   └─ callback(processed, file_size) → 进度回调
│   └─ 读到空 chunk 时：写入 padder.finalize() + encryptor.finalize()（最后的 PKCS7 填充块）
│
└─ return (True, "加密成功", final_out_path)
```

### 7.2 解密流程

```
process_file_direct(file_path, target_path, key_bytes, is_encrypt=False, ...)
│
├─ [读取并解析文件头]
│   ├─ iv = f_in.read(16) → 长度不足则 return (False, "文件头损坏", "")
│   ├─ name_len = struct.unpack('>I', f_in.read(4))[0]
│   ├─ enc_fname_data = f_in.read(name_len)
│   └─ f_in.read(8) → 跳过 OriginSize（当前版本未使用此字段）
│
├─ [解密文件名]
│   ├─ AES-CBC 解密 enc_fname_data（使用头部读出的 IV）
│   ├─ PKCS7 去填充
│   ├─ UTF-8 解码得到 orig_name
│   └─ 任何异常（ValueError/其他）→ return (False, "密钥错误", "")
│
├─ [确定实际输出路径]
│   └─ final_out_path = target_dir / orig_name   ← 强制使用恢复的原始文件名，忽略传入文件名
│
├─ [计算数据区大小]
│   ├─ header_size = 16 + 4 + name_len + 8
│   ├─ data_size = total_file_size - header_size
│   └─ data_size = max(data_size, 1)   ← 防止除零
│
├─ [分块解密主体（流式处理）]
│   ├─ AES-CBC Decryptor + PKCS7 Unpadder
│   ├─ 循环读取 chunk_size 大小的数据块
│   │   ├─ 检查 controller.is_stop_requested() → 抛出 InterruptedError
│   │   ├─ 检查 controller.wait_if_paused()
│   │   ├─ unpadder.update(decryptor.update(chunk)) → 流式解密
│   │   └─ callback(processed, data_size) → 进度回调
│   └─ 读到空 chunk 时：unpadder.update(decryptor.finalize()) + unpadder.finalize()
│
└─ return (True, "解密成功", final_out_path)
```

### 7.3 中断处理

两个流程均通过外层 `try/except InterruptedError` 处理用户停止操作：

```python
except InterruptedError:
    if os.path.exists(final_out_path):
        try: os.remove(final_out_path)   # 立即删除未完成的输出文件，防止损坏残留
        except: pass
    return False, "用户停止", ""
```

---

## 8. 多线程与多进程架构

### 8.1 架构概览

```
MainWindow（主线程）
│
│  用户点击"开始加密/解密"
│
└──► BatchWorkerThread（QThread 工作线程）
      │
      │  使用 ProcessPoolExecutor 管理进程池
      │  max_workers = min(os.cpu_count(), len(valid_files
