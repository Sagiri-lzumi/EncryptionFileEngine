import os
import sys

# =========================================================
# 路径核心逻辑
# =========================================================
if getattr(sys, 'frozen', False):
    # 【打包环境】
    # 如果是打包后的 exe，基准目录 = exe 所在的文件夹
    # 这样 Logs 和 Keys 就会生成在 exe 旁边
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 【开发环境】
    # 如果是脚本运行，基准目录 = config.py 所在的文件夹
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# 目录定义
# =========================================================
DIRS = {
    # 这些文件夹都会生成在 BASE_DIR 下
    "ORIGINAL": os.path.join(BASE_DIR, "OriginalFile"),
    "ENCRYPTED": os.path.join(BASE_DIR, "EncryptedFile"),
    "DECRYPTED": os.path.join(BASE_DIR, "DecryptedFile"),
    "KEYS": os.path.join(BASE_DIR, "Keys"),
    "LOGS": os.path.join(BASE_DIR, "Logs")
}

# 智能分块策略
CHUNK_SIZES = {
    "SMALL": 64 * 1024,        # 64KB
    "MEDIUM": 1024 * 1024,     # 1MB
    "LARGE": 10 * 1024 * 1024, # 10MB
    "HUGE": 64 * 1024 * 1024   # 64MB
}

def init_directories():
    """初始化所有必要目录"""
    for path in DIRS.values():
        if not os.path.exists(path):
            os.makedirs(path)