import logging
import os
import sys
from config import DIRS
from datetime import datetime


class LoggerService:
    def __init__(self):
        self.logger = logging.getLogger("EncryptionEngineCore")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.propagate = False  # 防止日志向上传递导致重复
        self.file_handler_set = False  # 标记是否已经配置过文件

    def _setup_file_handler(self):
        """只在第一次需要写入日志时调用，确保只有主进程会创建文件"""
        if self.file_handler_set:
            return

        try:
            # 1. 确保日志目录
            log_dir = DIRS["LOGS"]
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 2. 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.log_file = os.path.join(log_dir, f"system_{timestamp}.log")

            # 3. 配置 FileHandler
            # 使用 utf-8 编码，append 模式
            file_handler = logging.FileHandler(self.log_file, mode='a', encoding='utf-8', delay=False)
            file_handler.setLevel(logging.INFO)

            formatter = logging.Formatter(
                '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.file_handler_set = True

            # 在控制台提示文件位置，确认创建成功
            print(f"📄 [系统日志] 日志文件已锁定: {os.path.abspath(self.log_file)}")

        except Exception as e:
            print(f"❌ [日志错误] 无法初始化日志文件: {e}")

    def log(self, message, level="info"):
        # [核心改动] 懒加载：第一次调用 log 时才去创建文件
        if not self.file_handler_set:
            self._setup_file_handler()

        # 控制台打印
        print(f"[{level.upper()}] {message}")

        # 写入文件
        if level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)

        # 强制刷新缓冲区，确保掉电不丢数据
        for h in self.logger.handlers:
            h.flush()


sys_logger = LoggerService()