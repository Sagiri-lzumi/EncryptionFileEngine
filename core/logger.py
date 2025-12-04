import logging
import os
from config import DIRS
from datetime import datetime


class LoggerService:
    def __init__(self):
        # 强制检查目录
        log_dir = DIRS["LOGS"]
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        self.log_file = os.path.join(log_dir, f"system_{datetime.now().strftime('%Y%m%d')}.log")

        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            # [修正点] 使用 utf-8-sig，完美兼容 Windows 记事本
            encoding='utf-8-sig'
        )

    def log(self, message, level="info"):
        print(f"[{level.upper()}] {message}")
        if level == "info":
            logging.info(message)
        elif level == "error":
            logging.error(message)
        elif level == "warning":
            logging.warning(message)


sys_logger = LoggerService()