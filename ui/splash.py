from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPainterPath, QRegion
import math


class IntroScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 300)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 设置圆角遮罩
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, 500, 300), 20, 20)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

        self.progress = 0
        self.loading_text = "Loading"
        self._opacity = 0.0
        self._logo_scale = 0.0
        self._progress_width = 0.0

        # 淡入动画
        self._fade_anim = QPropertyAnimation(self, b"opacity", self)
        self._fade_anim.setDuration(400)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

        # Logo缩放动画
        self._logo_anim = QPropertyAnimation(self, b"logoScale", self)
        self._logo_anim.setDuration(600)
        self._logo_anim.setEasingCurve(QEasingCurve.OutBack)
        self._logo_anim.setStartValue(0.0)
        self._logo_anim.setEndValue(1.0)
        QTimer.singleShot(200, self._logo_anim.start)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, v):
        self._opacity = v
        self.update()

    def get_logo_scale(self):
        return self._logo_scale

    def set_logo_scale(self, v):
        self._logo_scale = v
        self.update()

    def get_progress_width(self):
        return self._progress_width

    def set_progress_width(self, v):
        self._progress_width = v
        self.update()

    opacity = Property(float, get_opacity, set_opacity)
    logoScale = Property(float, get_logo_scale, set_logo_scale)
    progressWidth = Property(float, get_progress_width, set_progress_width)

    def animate(self):
        self.update()

    def update_progress(self, val, msg):
        self.progress = val
        self.loading_text = msg

        # 进度条动画
        anim = QPropertyAnimation(self, b"progressWidth", self)
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setEndValue(val / 100.0)
        anim.start()

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        w, h = self.width(), self.height()

        # 白色圆角背景
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 20, 20)
        painter.fillPath(path, QColor("#FFFFFF"))

        # Logo (带缩放动画)
        if self._logo_scale > 0:
            painter.save()
            cx, cy = w // 2, h // 2 - 40
            painter.translate(cx, cy)
            painter.scale(self._logo_scale, self._logo_scale)
            painter.translate(-cx, -cy)

            painter.setPen(QPen(QColor("#007AFF"), 4))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(cx - 25, cy - 15, 50, 35, 8, 8)
            painter.drawArc(cx - 20, cy - 35, 40, 30, 0, 180 * 16)

            painter.restore()

        # 标题
        painter.setPen(QColor("#1D1D1F"))
        painter.setFont(QFont("Segoe UI", 22, QFont.Bold))
        painter.drawText(0, h // 2 + 10, w, 40, Qt.AlignCenter, "Encryption Studio")

        # 加载文本
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#86868B"))
        painter.drawText(0, h // 2 + 50, w, 30, Qt.AlignCenter, self.loading_text)

        # 进度条
        bar_w = 200
        bar_x = (w - bar_w) // 2
        bar_y = h // 2 + 90

        painter.fillRect(bar_x, bar_y, bar_w, 4, QColor("#E5E5EA"))
        if self._progress_width > 0:
            progress_w = int(bar_w * self._progress_width)
            painter.fillRect(bar_x, bar_y, progress_w, 4, QColor("#007AFF"))
