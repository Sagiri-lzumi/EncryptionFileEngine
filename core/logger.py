import logging
import logging.handlers
import os
import sys
# import colorama  <-- 删除了这行顶层的引用
from datetime import datetime
from config import DIRS

# ==========================================
# 颜色引擎初始化 (安全降级模式)
# ==========================================
try:
    import colorama
    from colorama import init, Fore, Style

    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # 如果没有安装 colorama，使用空字符串代替颜色代码，防止报错
    HAS_COLOR = False


    class Fore:
        BLUE = GREEN = YELLOW = RED = WHITE = CYAN = ""


    class Style:
        BRIGHT = RESET_ALL = ""


class LogFormatter(logging.Formatter):
    """
    自定义日志格式化器
    1. 控制台带颜色 (如果可用)
    2. 文件纯文本
    3. 自动对齐列宽
    """

    # 定义日志格式：[时间] [进程:线程] [级别] [位置] 信息
    FMT_STR = (
        "%(asctime)s.%(msecs)03d "
        "| %(processName)s:%(threadName)s "
        "| %(levelname)-8s "
        "| %(filename)s:%(lineno)d "
        "| %(message)s"
    )

    DATE_FMT = '%Y-%m-%d %H:%M:%S'

    # 颜色映射
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED + Style.BRIGHT,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def __init__(self, use_color=False):
        super().__init__(self.FMT_STR, self.DATE_FMT)
        # 只有当系统支持且用户请求颜色时才开启
        self.use_color = use_color and HAS_COLOR

    def format(self, record):
        # 1. 保存原始信息，防止被修改
        original_levelname = record.levelname

        # 2. 如果需要颜色，修饰 levelname
        if self.use_color:
            color = self.COLORS.get(record.levelno, Fore.WHITE)
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"

            # 错误级别高亮 message
            if record.levelno >= logging.ERROR:
                record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"

        # 3. 调用父类格式化
        formatted_msg = super().format(record)

        # 4. 恢复原始 levelname (防止污染其他 handler)
        record.levelname = original_levelname

        return formatted_msg


class LoggerService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggerService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = logging.getLogger("EncryptionEngineCore")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.handlers_setup = False
        self._initialized = True

    def _setup_handlers(self):
        """懒加载：配置控制台和文件处理器"""
        if self.handlers_setup:
            return

        try:
            # 1. 确保日志目录
            log_dir = DIRS["LOGS"]
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            # 2. 生成文件名 (修改处：Encrypt_年月日_时分秒.log)
            # 例如: Encrypt_20251204_205208.log
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"Encrypt_{timestamp}.log"
            log_file = os.path.join(log_dir, log_filename)

            # --- Handler A: 文件 (带轮转，最大 10MB，保留 5 个备份) ---
            # 注意：由于文件名包含秒级时间戳，每次重启程序都会生成新文件。
            # RotatingFileHandler 在这里主要防止单次运行日志过大 (超过10MB会切分)。
            # delay=False 确保立即创建文件，避免权限问题延后暴露
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8',
                delay=False
            )
            file_handler.setLevel(logging.INFO)
            # 文件日志强制不使用颜色
            file_handler.setFormatter(LogFormatter(use_color=False))

            # --- Handler B: 控制台 (尝试使用颜色) ---
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(LogFormatter(use_color=True))

            # 清除旧的 handlers
            self.logger.handlers.clear()

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

            self.handlers_setup = True

            self.logger.info(f"日志系统初始化完成。日志路径: {os.path.abspath(log_file)}")
            if not HAS_COLOR:
                self.logger.info("提示: 未检测到 colorama 库，日志将以纯文本显示。")

        except Exception as e:
            print(f"❌ [CRITICAL] 无法初始化日志系统: {e}")

    def log(self, message, level="info"):
        """
        兼容旧代码的 wrapper 方法。
        """
        if not self.handlers_setup:
            self._setup_handlers()

        lvl_map = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "debug": logging.DEBUG,
            "critical": logging.CRITICAL
        }

        log_level = lvl_map.get(level.lower(), logging.INFO)

        # 使用 stacklevel=2 确保日志显示的行号是调用 log() 的地方
        if sys.version_info >= (3, 8):
            self.logger.log(log_level, message, stacklevel=2)
        else:
            self.logger.log(log_level, message)

        # 强制刷新
        for h in self.logger.handlers:
            h.flush()


# 全局单例
sys_logger = LoggerService()