from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
# [重要] 确保导入了所有必要的绘图类
from PySide6.QtGui import (QColor, QFont, QPainter, QPen, QConicalGradient,
                           QRadialGradient, QLinearGradient, QBrush, QPainterPath)
import math


class IntroScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        # 尺寸稍微拉宽一点，更有电影感
        self.setFixedSize(500, 320)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 动画变量
        self.angle_fast = 0
        self.angle_slow = 0
        self.pulse_scale = 1.0
        self.pulse_direction = 0.02

        self.loading_text = "CORE INITIALIZING..."
        self.progress = 0

        # 60FPS 极顺滑刷新 (约16ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def animate(self):
        # 旋转角度更新
        self.angle_fast = (self.angle_fast + 12) % 360
        self.angle_slow = (self.angle_slow - 5) % 360

        # 呼吸缩放效果 (在 0.95 到 1.05 之间波动)
        self.pulse_scale += self.pulse_direction
        if self.pulse_scale > 1.05 or self.pulse_scale < 0.95:
            self.pulse_direction *= -1

        self.update()  # 触发重绘

    def update_progress(self, val, msg):
        self.progress = val
        # 让文字看起来像是代码在跳动
        self.loading_text = f">_{msg.upper()}"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # 开启高质量抗锯齿
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        rect = self.rect()
        cx, cy = w // 2, h // 2 - 15

        # =================================================
        # 1. 绘制背景 (深空径向渐变，营造景深)
        # =================================================
        bg_rect = rect.adjusted(5, 5, -5, -5)
        # 径向渐变中心点在画面中心稍偏上
        bg_grad = QRadialGradient(cx, cy, w * 0.8)
        bg_grad.setColorAt(0.0, QColor("#1a1b20"))  # 中心稍亮
        bg_grad.setColorAt(1.0, QColor("#090a0c"))  # 边缘极暗

        painter.setBrush(bg_grad)
        painter.setPen(QPen(QColor("#2a2b30"), 1))  # 微弱的边框光
        painter.drawRoundedRect(bg_rect, 15, 15)

        # =================================================
        # 2. 绘制中心能量核心 (呼吸光点)
        # =================================================
        painter.save()
        painter.translate(cx, cy)
        painter.scale(self.pulse_scale, self.pulse_scale)

        # 核心高亮
        core_grad = QRadialGradient(0, 0, 20)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 200))  # 极亮白芯
        core_grad.setColorAt(0.3, QColor("#00e5ff"))  # 青色光晕
        core_grad.setColorAt(1.0, Qt.transparent)

        painter.setPen(Qt.NoPen)
        painter.setBrush(core_grad)
        painter.drawEllipse(QPointF(0, 0), 20, 20)
        painter.restore()

        # =================================================
        # 3. 绘制动态能量环 (多层光晕叠加)
        # =================================================

        # --- 外圈高速环 (青色) ---
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_fast)

        # 使用锥形渐变模拟扫描尾迹
        grad_fast = QConicalGradient(0, 0, 0)
        grad_fast.setColorAt(0.0, QColor("#00e5ff"))  # 亮青头
        grad_fast.setColorAt(0.2, QColor(0, 229, 255, 50))  # 半透明尾
        grad_fast.setColorAt(1.0, Qt.transparent)

        pen_fast = QPen(grad_fast, 6)  # 线条宽度
        pen_fast.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_fast)
        # 只画一段弧线，模拟彗星尾巴
        radius_fast = 60
        painter.drawArc(QRectF(-radius_fast, -radius_fast, radius_fast * 2, radius_fast * 2), 0, 270 * 16)

        # 增加一层辉光底色
        pen_glow = QPen(QColor(0, 229, 255, 30), 12)
        painter.setPen(pen_glow)
        painter.drawArc(QRectF(-radius_fast, -radius_fast, radius_fast * 2, radius_fast * 2), 10 * 16, 250 * 16)
        painter.restore()

        # --- 内圈慢速环 (洋红色，反向) ---
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_slow)

        grad_slow = QConicalGradient(0, 0, 180)
        grad_slow.setColorAt(0.0, QColor("#ff0055"))  # 洋红头
        grad_slow.setColorAt(0.3, QColor(255, 0, 85, 40))
        grad_slow.setColorAt(1.0, Qt.transparent)

        pen_slow = QPen(grad_slow, 4)
        pen_slow.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_slow)
        radius_slow = 45
        painter.drawArc(QRectF(-radius_slow, -radius_slow, radius_slow * 2, radius_slow * 2), 0, 220 * 16)
        painter.restore()

        # =================================================
        # 4. 绘制文字信息
        # =================================================

        # 主标题 (带微弱辉光)
        title_font = QFont("Segoe UI", 22, QFont.Bold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        painter.setFont(title_font)

        # 辉光层
        painter.setPen(QColor(0, 229, 255, 30))
        painter.drawText(QRectF(0, h - 110, w, 40), Qt.AlignCenter, "ENCRYPTION CORE")
        # 实体层
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(0, h - 110, w, 40), Qt.AlignCenter, "ENCRYPTION CORE")

        # 加载状态文字
        status_font = QFont("Consolas", 9)
        painter.setFont(status_font)
        painter.setPen(QColor("#00e5ff"))  # 青色文字
        painter.drawText(QRectF(40, h - 50, w - 80, 20), Qt.AlignLeft | Qt.AlignVCenter, self.loading_text)

        # 百分比
        painter.setPen(QColor("#666666"))
        painter.drawText(QRectF(40, h - 50, w - 80, 20), Qt.AlignRight | Qt.AlignVCenter, f"[{self.progress}%]")

        # =================================================
        # 5. 极简进度条 (底部细线)
        # =================================================
        bar_bg = QRectF(40, h - 25, w - 80, 3)
        painter.setBrush(QColor("#222222"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_bg, 1.5, 1.5)

        if self.progress > 0:
            bar_w = (w - 80) * (self.progress / 100.0)
            bar_fg = QRectF(40, h - 25, bar_w, 3)
            # 进度条渐变光
            bar_grad = QLinearGradient(40, 0, w - 40, 0)
            bar_grad.setColorAt(0, QColor("#00e5ff"))
            bar_grad.setColorAt(1, QColor("#ff0055"))
            painter.setBrush(bar_grad)
            painter.drawRoundedRect(bar_fg, 1.5, 1.5)