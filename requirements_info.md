# EncryptionFileEngine 依赖说明

## 系统要求

- **操作系统**: Windows 10/11 (推荐), macOS, Linux
- **Python 版本**: Python 3.8+

## Python 依赖库

### 核心依赖

```bash
pip install PySide6>=6.0.0
pip install cryptography>=41.0.0
pip install pycryptodome>=3.18.0
```

### 依赖说明

| 库名 | 版本要求 | 用途 |
|------|---------|------|
| PySide6 | >=6.0.0 | Qt6 GUI 框架，用于构建用户界面 |
| cryptography | >=41.0.0 | 加密库，提供 RSA、AES 加密功能 |
| pycryptodome | >=3.18.0 | 加密库，提供 AES、DES、DES3、ARC4 等多种加密算法 |

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd EncryptionFileEngine
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv
```

### 3. 激活虚拟环境

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. 安装依赖

```bash
pip install PySide6 cryptography pycryptodome
```

或使用 requirements.txt（如果提供）:
```bash
pip install -r requirements.txt
```

## 运行项目

```bash
python main.py
```

## 项目结构

```
EncryptionFileEngine/
├── main.py              # 程序入口
├── config.py            # 配置文件
├── core/                # 核心加密模块
│   ├── auth.py         # 用户认证
│   ├── file_cipher.py  # 文件加密引擎
│   ├── rsa_cipher.py   # RSA 密钥管理
│   ├── text_cipher.py  # 文本加密
│   └── logger.py       # 日志模块
├── ui/                  # 用户界面
│   ├── login.py        # 登录界面
│   ├── main_window.py  # 主窗口
│   ├── splash.py       # 启动画面
│   ├── themes.py       # 主题配置
│   ├── components.py   # UI 组件
│   └── utils.py        # UI 工具函数
├── Keys/                # 密钥存储目录
└── Logs/                # 日志目录
```

## 常见问题

### Q: 提示缺少 PySide6 模块
A: 确保已激活虚拟环境并安装了 PySide6：`pip install PySide6`

### Q: 提示 "No module named 'Crypto'"
A: 需要安装 pycryptodome：`pip install pycryptodome`

### Q: 加密功能报错
A: 检查加密库是否正确安装：`pip install --upgrade cryptography pycryptodome`

### Q: Windows 下无法运行
A: 确保使用管理员权限或检查防火墙设置

## 开发与打包依赖（可选）

如需打包成可执行文件，可选择以下任一工具：

### PyInstaller（推荐）
```bash
pip install pyinstaller
```

打包命令：
```bash
pyinstaller --onefile --windowed --icon=fileenc.ico main.py
```

### 其他打包工具

```bash
pip install cx_Freeze    # 跨平台打包工具
pip install Nuitka       # Python 编译器，性能更好
```

### 完整开发环境依赖

```bash
pip install pyinstaller pyinstaller-hooks-contrib
pip install cx_Freeze
pip install Nuitka
```

## requirements.txt

建议创建 `requirements.txt` 文件：

**运行时依赖 (requirements.txt):**
```
PySide6>=6.7.0
cryptography>=46.0.0
pycryptodome>=3.23.0
```

**开发依赖 (requirements-dev.txt):**
```
pyinstaller>=6.17.0
pyinstaller-hooks-contrib>=2025.10
cx_Freeze>=8.5.0
Nuitka>=2.8.9
```

安装方式：
```bash
# 仅运行时依赖
pip install -r requirements.txt

# 包含开发工具
pip install -r requirements.txt -r requirements-dev.txt
```
