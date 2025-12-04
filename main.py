import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from config import init_directories
from ui.splash import IntroScreen
from ui.main_window import MainWindow


def main():
    # 1. 优先初始化目录
    init_directories()

    # [修正点] PySide6 默认已开启高分屏缩放，删除了导致警告的旧代码

    app = QApplication(sys.argv)

    # 3. 显示能量启动页
    splash = IntroScreen()
    splash.show()

    # 精确控制加载时间为 1秒 (1000ms)
    steps = 50
    sleep_ms = 20

    for i in range(1, steps + 1):
        progress = int(i * (100 / steps))

        if progress < 30:
            msg = "Mounting Secure File System..."
        elif progress < 60:
            msg = "Verifying Cipher Algorithms..."
        elif progress < 85:
            msg = "Loading User Interface..."
        else:
            msg = "System Ready."

        splash.update_progress(progress, msg)

        QThread.msleep(sleep_ms)
        app.processEvents()

        # 4. 启动主界面
    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()