from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient, QLinearGradient
import math


class IntroScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 280)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.angle = 0
        self.pulse = 0
        self.progress = 0
        self.loading_text = "INITIALIZING..."
        self._opacity = 0.0

        # 淡入动画
        self._fade_anim = QPropertyAnimation(self, b"opacity", self)
        self._fade_anim.setDuration(800)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, v):
        self._opacity = v
        self.update()

    opacity = Property(float, get_opacity, set_opacity)

    def animate(self):
        self.angle = (self.angle + 3) % 360
        self.pulse = (self.pulse + 0.05) % (2 * math.pi)
        self.update()

    def update_progress(self, val, msg):
        self.progress = val
        self.loading_text = msg.upper()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 - 20

        # 背景
        bg_grad = QRadialGradient(cx, cy, w * 0.6)
        bg_grad.setColorAt(0, QColor("#1a1a1a"))
        bg_grad.setColorAt(1, QColor("#0a0a0a"))
        painter.setBrush(bg_grad)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

        # 旋转光环
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle)

        for i in range(3):
            radius = 50 + i * 15
            opacity = int(100 - i * 30)
            painter.setPen(QPen(QColor(92, 107, 192, opacity), 3))
            painter.drawEllipse(QPointF(0, 0), radius, radius)

        painter.restore()

        # 中心脉冲点
        pulse_size = 15 + math.sin(self.pulse) * 5
        core_grad = QRadialGradient(cx, cy, pulse_size)
        core_grad.setColorAt(0, QColor(255, 255, 255, 200))
        core_grad.setColorAt(0.5, QColor(92, 107, 192, 150))
        core_grad.setColorAt(1, Qt.transparent)
        painter.setBrush(core_grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), pulse_size, pulse_size)

        # 标题
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
        painter.drawText(0, h - 100, w, 30, Qt.AlignCenter, "ENCRYPTION STUDIO")

        # 状态文本
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#888888"))
        painter.drawText(0, h - 70, w, 20, Qt.AlignCenter, self.loading_text)

        # 进度条
        bar_w = w - 100
        bar_x = 50
        bar_y = h - 40

        painter.fillRect(bar_x, bar_y, bar_w, 4, QColor("#222222"))

        if self.progress > 0:
            progress_w = int(bar_w * self.progress / 100)
            bar_grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            bar_grad.setColorAt(0, QColor("#5c6bc0"))
            bar_grad.setColorAt(1, QColor("#7986cb"))
            painter.fillRect(bar_x, bar_y, progress_w, 4, bar_grad)

        # 百分比
        painter.setPen(QColor("#5c6bc0"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(0, h - 20, w, 15, Qt.AlignCenter, f"{self.progress}%")