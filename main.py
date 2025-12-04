import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from config import init_directories
from ui.splash import IntroScreen
from ui.main_window import MainWindow
#first

def main():
    init_directories()
    app = QApplication(sys.argv)

    splash = IntroScreen()
    splash.show()

    # 模拟加载
    for i in range(1, 101):
        splash.update_progress(i, "Loading Security Core..." if i < 60 else "Optimizing Layout...")
        QThread.msleep(20)
        app.processEvents()

    # 直接进主界面 (无鉴权)
    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()