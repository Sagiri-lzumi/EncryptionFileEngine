import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from config import init_directories
from ui.splash import IntroScreen
from ui.main_window import MainWindow


def main():
    # 1. 优先初始化目录
    init_directories()

    # 2. 设置高分屏支持 (可选，让界面更清晰)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    # 3. 显示全新的能量启动页
    splash = IntroScreen()
    splash.show()

    # ==========================================
    # 精确控制加载时间为 1秒 (1000ms)
    # 策略: 循环 50 次，每次休眠 20ms
    # Total = 50 * 20 = 1000ms
    # ==========================================
    steps = 50
    sleep_ms = 20

    for i in range(1, steps + 1):
        # 计算当前百分比 (i * (100/steps))
        progress = int(i * (100 / steps))

        # 模拟不同的加载阶段文案
        if progress < 30:
            msg = "Mounting Secure File System..."
        elif progress < 60:
            msg = "Verifying Cipher Algorithms..."
        elif progress < 85:
            msg = "Loading User Interface..."
        else:
            msg = "System Ready."

        splash.update_progress(progress, msg)

        # 核心: 精确休眠
        QThread.msleep(sleep_ms)
        # 核心: 强制处理绘图事件，确保动画流畅
        app.processEvents()

        # 4. 启动主界面并平滑切换
    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    # 需要导入 Qt 用于设置高分屏属性
    from PySide6.QtCore import Qt

    main()