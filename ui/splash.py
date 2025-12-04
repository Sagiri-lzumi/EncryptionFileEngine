from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt, QTimer, QRectF
# [修正点] 补全了 QLinearGradient 的导入
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QConicalGradient, QRadialGradient, QBrush, QLinearGradient


class IntroScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(450, 300)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 动画变量
        self.angle_outer = 0
        self.angle_inner = 0
        self.pulse_val = 0
        self.loading_text = "SYSTEM BOOT..."
        self.progress = 0

        # 60FPS 极顺滑刷新 (约16ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def animate(self):
        # 外圈快转
        self.angle_outer = (self.angle_outer + 8) % 360
        # 内圈慢转反向
        self.angle_inner = (self.angle_inner - 4) % 360
        # 呼吸效果 (0-255循环)
        self.pulse_val = (self.pulse_val + 5) % 180
        self.update()

    def update_progress(self, val, msg):
        self.progress = val
        self.loading_text = msg.upper()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        rect = self.rect()

        # 1. 绘制背景 (深空灰卡片)
        bg_rect = rect.adjusted(5, 5, -5, -5)
        painter.setBrush(QColor("#0f1012"))
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawRoundedRect(bg_rect, 12, 12)

        # 2. 中心坐标
        cx, cy = w // 2, h // 2 - 20

        # 3. 绘制外圈光环 (High Speed Ring)
        grad_outer = QConicalGradient(cx, cy, -self.angle_outer)
        grad_outer.setColorAt(0, QColor("#00e5ff"))  # 亮青色
        grad_outer.setColorAt(0.1, QColor("#00e5ff"))
        grad_outer.setColorAt(0.5, Qt.transparent)
        grad_outer.setColorAt(1, Qt.transparent)

        painter.setPen(Qt.NoPen)
        painter.setBrush(grad_outer)

        # 绘制圆环
        painter.drawPie(cx - 50, cy - 50, 100, 100, 0, 360 * 16)

        # 4. 绘制内圈 (Data Ring)
        grad_inner = QConicalGradient(cx, cy, -self.angle_inner)
        grad_inner.setColorAt(0, QColor("#ff0055"))  # 赛博红
        grad_inner.setColorAt(0.2, Qt.transparent)

        painter.setBrush(grad_inner)
        painter.drawPie(cx - 35, cy - 35, 70, 70, 0, 360 * 16)

        # 5. 挖空中心，形成圆环感，并做呼吸背景
        painter.setPen(Qt.NoPen)
        # 计算呼吸透明度
        alpha = 100 + abs(90 - self.pulse_val)  # 100~190
        painter.setBrush(QColor(20, 20, 25, 255))
        painter.drawEllipse(cx - 30, cy - 30, 60, 60)

        # 6. 中心 Logo / 文字
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(cx - 30, cy - 30, 60, 60), Qt.AlignCenter, "SEC")

        # 7. 底部文字信息
        painter.setPen(QColor("#888888"))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(QRectF(0, h - 70, w, 20), Qt.AlignCenter, f"{self.loading_text} [{self.progress}%]")

        # 8. 底部极细进度条
        bar_bg_rect = QRectF(40, h - 30, w - 80, 4)
        # 背景槽
        painter.setBrush(QColor("#222222"))
        painter.drawRoundedRect(bar_bg_rect, 2, 2)

        # 进度条
        if self.progress > 0:
            bar_width = (w - 80) * (self.progress / 100.0)
            bar_fg_rect = QRectF(40, h - 30, bar_width, 4)

            # [修正点] 这里的 QLinearGradient 现在可以正常工作了
            bar_grad = QLinearGradient(40, 0, w - 40, 0)
            bar_grad.setColorAt(0, QColor("#00e5ff"))
            bar_grad.setColorAt(1, QColor("#007acc"))
            painter.setBrush(bar_grad)
            painter.drawRoundedRect(bar_fg_rect, 2, 2)