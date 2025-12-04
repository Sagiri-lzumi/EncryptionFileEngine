# config.py
import os

# 0x01 程序结构目录定义
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    "ORIGINAL": os.path.join(BASE_DIR, "OriginalFile"),
    "ENCRYPTED": os.path.join(BASE_DIR, "EncryptedFile"),
    "DECRYPTED": os.path.join(BASE_DIR, "DecryptedFile"),
    "KEYS": os.path.join(BASE_DIR, "Keys"),
    "LOGS": os.path.join(BASE_DIR, "Logs")
}

# 初始化目录
def init_directories():
    for path in DIRS.values():
        if not os.path.exists(path):
            os.makedirs(path)

# 默认分块大小选项 (4.1.2)
CHUNK_SIZES = {
    "64KB (快速/小文件)": 64 * 1024,
    "1MB (标准)": 1024 * 1024,
    "10MB (大文件优化)": 10 * 1024 * 1024,
    "64MB (超大文件)": 64 * 1024 * 1024
}