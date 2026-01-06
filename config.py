import os
import sys

# =========================================================
# 路径核心逻辑
# =========================================================
if getattr(sys, 'frozen', False):
    # 【打包环境】
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 【开发环境】
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# 目录定义
# =========================================================
DIRS = {
    "ORIGINAL": os.path.join(BASE_DIR, "OriginalFile"),
    "ENCRYPTED": os.path.join(BASE_DIR, "EncryptedFile"),
    "DECRYPTED": os.path.join(BASE_DIR, "DecryptedFile"),
    "KEYS": os.path.join(BASE_DIR, "Keys"),
    "LOGS": os.path.join(BASE_DIR, "Logs"),
    # [注意] 这里故意不定义 TEMP/SSD 目录，强制由用户在 UI 指定
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
        if path and not os.path.exists(path):
            os.makedirs(path)