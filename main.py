import sys
import multiprocessing
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from config import init_directories
from ui.splash import IntroScreen
from ui.main_window import MainWindow


def main():
    # 1. Windows 多进程打包必须
    multiprocessing.freeze_support()

    init_directories()
    app = QApplication(sys.argv)

    splash = IntroScreen()
    splash.show()

    # 1秒 极速启动
    for i in range(1, 51):
        splash.update_progress(i * 2, "LOADING KERNEL..." if i < 25 else "STARTING UI...")
        QThread.msleep(20)
        app.processEvents()

    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()