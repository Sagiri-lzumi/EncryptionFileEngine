import sys
import os
import ctypes
import multiprocessing
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from PySide6.QtGui import QIcon

from config import init_directories, BASE_DIR
from ui.splash import IntroScreen
from ui.main_window import MainWindow

def main():
    # 1. Windows 多进程打包必须
    multiprocessing.freeze_support()

    # 2. 提示 Windows 这是一个独立的应用程序
    try:
        myappid = 'security.fileengine.cipher.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

    init_directories()
    app = QApplication(sys.argv)

    # 3. 设置全局应用图标
    icon_path = os.path.join(BASE_DIR, "fileenc.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    splash = IntroScreen()
    splash.show()

    # 模拟加载过程
    for i in range(1, 51):
        splash.update_progress(i * 2, "LOADING KERNEL..." if i < 25 else "STARTING UI...")
        QThread.msleep(10)
        app.processEvents()

    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()