import logging
import os
from config import DIRS
from datetime import datetime


class LoggerService:
    def __init__(self):
        # 1. 确保日志目录存在
        log_dir = DIRS["LOGS"]
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 2. 生成带时间戳的日志文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(log_dir, f"system_{timestamp}.log")

        # 3. [关键修复] 创建独立的 Logger 实例，不依赖根 Logger
        self.logger = logging.getLogger("EncryptionEngineCore")
        self.logger.setLevel(logging.INFO)

        # 清除可能存在的旧 Handler，防止重复写入
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # 4. [关键修复] 显式配置 FileHandler
        # delay=False 确保立即创建文件
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8-sig', delay=False)
        file_handler.setLevel(logging.INFO)

        # 设置格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # 添加到 logger
        self.logger.addHandler(file_handler)

    def log(self, message, level="info"):
        # 同时输出到控制台方便调试
        print(f"[{level.upper()}] {message}")

        if level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)

        # [可选] 强制刷新缓冲区，确保日志不丢失 (会轻微影响性能，但在桌面应用中可接受)
        for h in self.logger.handlers:
            h.flush()


sys_logger = LoggerService()