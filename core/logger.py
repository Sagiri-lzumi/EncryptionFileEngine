import logging
import logging.handlers
import os
import sys
from datetime import datetime
from config import DIRS


class LogFormatter(logging.Formatter):
    FMT_STR = "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    DATE_FMT = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        super().__init__(self.FMT_STR, self.DATE_FMT)


class LoggerService:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.logger = logging.getLogger("EncryptionEngine")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self._initialized = True
        self._setup_handlers()

    def _setup_handlers(self):
        log_dir = DIRS["LOGS"]
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"Encrypt_{timestamp}.log")

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(LogFormatter())

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(LogFormatter())

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.info(f"日志系统初始化完成: {log_file}")

    def log(self, message, level="info"):
        level_map = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "debug": logging.DEBUG,
            "critical": logging.CRITICAL
        }
        log_level = level_map.get(level.lower(), logging.INFO)
        self.logger.log(log_level, message, stacklevel=2)


sys_logger = LoggerService()