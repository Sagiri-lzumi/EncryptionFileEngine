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
        self.logger.propagate = False
        self.file_handler_set = False

    def _setup_file_handler(self):
        if self.file_handler_set:
            return

        try:
            log_dir = DIRS["LOGS"]
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.log_file = os.path.join(log_dir, f"system_{timestamp}.log")

            file_handler = logging.FileHandler(self.log_file, mode='a', encoding='utf-8', delay=False)
            file_handler.setLevel(logging.INFO)

            formatter = logging.Formatter(
                '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.file_handler_set = True

            print(f"📄 [系统日志] 日志文件已锁定: {os.path.abspath(self.log_file)}")

        except Exception as e:
            print(f"❌ [日志错误] 无法初始化日志文件: {e}")

    def log(self, message, level="info"):
        if not self.file_handler_set:
            self._setup_file_handler()

        print(f"[{level.upper()}] {message}")

        if level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)

        for h in self.logger.handlers:
            h.flush()


sys_logger = LoggerService()