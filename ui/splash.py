from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (QColor, QFont, QPainter, QPen, QConicalGradient,
                           QRadialGradient, QLinearGradient, QBrush, QPainterPath)
import math


class IntroScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 320)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.angle_fast = 0
        self.angle_slow = 0
        self.pulse_scale = 1.0
        self.pulse_direction = 0.02

        self.loading_text = "CORE INITIALIZING..."
        self.progress = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def animate(self):
        self.angle_fast = (self.angle_fast + 12) % 360
        self.angle_slow = (self.angle_slow - 5) % 360

        self.pulse_scale += self.pulse_direction
        if self.pulse_scale > 1.05 or self.pulse_scale < 0.95:
            self.pulse_direction *= -1

        self.update()

    def update_progress(self, val, msg):
        self.progress = val
        self.loading_text = f">_{msg.upper()}"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        rect = self.rect()
        cx, cy = w // 2, h // 2 - 15

        # 1. 绘制背景
        bg_rect = rect.adjusted(5, 5, -5, -5)
        bg_grad = QRadialGradient(cx, cy, w * 0.8)
        bg_grad.setColorAt(0.0, QColor("#1a1b20"))
        bg_grad.setColorAt(1.0, QColor("#090a0c"))

        painter.setBrush(bg_grad)
        painter.setPen(QPen(QColor("#2a2b30"), 1))
        painter.drawRoundedRect(bg_rect, 15, 15)

        # 2. 绘制中心能量核心
        painter.save()
        painter.translate(cx, cy)
        painter.scale(self.pulse_scale, self.pulse_scale)

        core_grad = QRadialGradient(0, 0, 20)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 200))
        core_grad.setColorAt(0.3, QColor("#00e5ff"))
        core_grad.setColorAt(1.0, Qt.transparent)

        painter.setPen(Qt.NoPen)
        painter.setBrush(core_grad)
        painter.drawEllipse(QPointF(0, 0), 20, 20)
        painter.restore()

        # 3. 绘制动态能量环
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_fast)

        grad_fast = QConicalGradient(0, 0, 0)
        grad_fast.setColorAt(0.0, QColor("#00e5ff"))
        grad_fast.setColorAt(0.2, QColor(0, 229, 255, 50))
        grad_fast.setColorAt(1.0, Qt.transparent)

        pen_fast = QPen(grad_fast, 6)
        pen_fast.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_fast)
        radius_fast = 60
        painter.drawArc(QRectF(-radius_fast, -radius_fast, radius_fast * 2, radius_fast * 2), 0, 270 * 16)

        pen_glow = QPen(QColor(0, 229, 255, 30), 12)
        painter.setPen(pen_glow)
        painter.drawArc(QRectF(-radius_fast, -radius_fast, radius_fast * 2, radius_fast * 2), 10 * 16, 250 * 16)
        painter.restore()

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_slow)

        grad_slow = QConicalGradient(0, 0, 180)
        grad_slow.setColorAt(0.0, QColor("#ff0055"))
        grad_slow.setColorAt(0.3, QColor(255, 0, 85, 40))
        grad_slow.setColorAt(1.0, Qt.transparent)

        pen_slow = QPen(grad_slow, 4)
        pen_slow.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_slow)
        radius_slow = 45
        painter.drawArc(QRectF(-radius_slow, -radius_slow, radius_slow * 2, radius_slow * 2), 0, 220 * 16)
        painter.restore()

        # 4. 绘制文字信息
        title_font = QFont("Segoe UI", 22, QFont.Bold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        painter.setFont(title_font)

        painter.setPen(QColor(0, 229, 255, 30))
        painter.drawText(QRectF(0, h - 110, w, 40), Qt.AlignCenter, "ENCRYPTION CORE")
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, h - 110, w, 40), Qt.AlignCenter, "ENCRYPTION CORE")

        status_font = QFont("Consolas", 9)
        painter.setFont(status_font)
        painter.setPen(QColor("#00e5ff"))
        painter.drawText(QRectF(40, h - 50, w - 80, 20), Qt.AlignLeft | Qt.AlignVCenter, self.loading_text)

        painter.setPen(QColor("#666666"))
        painter.drawText(QRectF(40, h - 50, w - 80, 20), Qt.AlignRight | Qt.AlignVCenter, f"[{self.progress}%]")

        # 5. 极简进度条
        bar_bg = QRectF(40, h - 25, w - 80, 3)
        painter.setBrush(QColor("#222222"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_bg, 1.5, 1.5)

        if self.progress > 0:
            bar_w = (w - 80) * (self.progress / 100.0)
            bar_fg = QRectF(40, h - 25, bar_w, 3)
            bar_grad = QLinearGradient(40, 0, w - 40, 0)
            bar_grad.setColorAt(0, QColor("#00e5ff"))
            bar_grad.setColorAt(1, QColor("#ff0055"))
            painter.setBrush(bar_grad)
            painter.drawRoundedRect(bar_fg, 1.5, 1.5)