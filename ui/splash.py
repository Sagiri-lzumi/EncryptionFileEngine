from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QFont, QPainter, QPen
import math


class IntroScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 300)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.progress = 0
        self.loading_text = "Loading..."
        self._opacity = 0.0
        self._dot_offset = 0

        # 淡入动画
        self._fade_anim = QPropertyAnimation(self, b"opacity", self)
        self._fade_anim.setDuration(600)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, v):
        self._opacity = v
        self.update()

    opacity = Property(float, get_opacity, set_opacity)

    def animate(self):
        self._dot_offset = (self._dot_offset + 1) % 4
        self.update()

    def update_progress(self, val, msg):
        self.progress = val
        self.loading_text = msg
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        w, h = self.width(), self.height()

        # 白色背景
        painter.fillRect(self.rect(), QColor("#FFFFFF"))

        # Logo图标 (简化的锁图标)
        cx, cy = w // 2, h // 2 - 40
        painter.setPen(QPen(QColor("#007AFF"), 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(cx - 25, cy - 15, 50, 35, 8, 8)
        painter.drawArc(cx - 20, cy - 35, 40, 30, 0, 180 * 16)

        # 标题
        painter.setPen(QColor("#1D1D1F"))
        painter.setFont(QFont("SF Pro Display", 24, QFont.Bold))
        painter.drawText(0, cy + 50, w, 40, Qt.AlignCenter, "Encryption Studio")

        # 加载文本
        painter.setFont(QFont("SF Pro Text", 11))
        painter.setPen(QColor("#86868B"))
        dots = "." * (self._dot_offset + 1)
        painter.drawText(0, cy + 90, w, 30, Qt.AlignCenter, self.loading_text + dots)

        # 进度条
        bar_w = 200
        bar_x = (w - bar_w) // 2
        bar_y = cy + 130

        painter.fillRect(bar_x, bar_y, bar_w, 3, QColor("#E5E5EA"))
        if self.progress > 0:
            progress_w = int(bar_w * self.progress / 100)
            painter.fillRect(bar_x, bar_y, progress_w, 3, QColor("#007AFF"))
