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

        # [修改点] 文件名加上 _%H%M%S (时分秒)，确保每次启动都是独立文件
        # 例如: system_20231201_143005.log
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(log_dir, f"system_{timestamp}.log")

        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            # 日志每一行的格式
            format='%(asctime)s - %(levelname)s - %(message)s',
            # 保持 utf-8-sig 以兼容 Windows 记事本
            encoding='utf-8-sig'
        )

    def log(self, message, level="info"):
        # 控制台输出一份，方便调试
        print(f"[{level.upper()}] {message}")

        if level == "info":
            logging.info(message)
        elif level == "error":
            logging.error(message)
        elif level == "warning":
            logging.warning(message)


sys_logger = LoggerService()