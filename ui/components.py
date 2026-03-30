from PySide6.QtWidgets import QPushButton, QListWidget, QAbstractItemView, QCheckBox, QStyle, QStyleOptionButton, QWidget, QGraphicsBlurEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRectF, Property, QRect, QPoint, QParallelAnimationGroup, Signal
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen, QFont
import os

from ui.platform_fonts import get_system_font_family


class GlassWidget(QWidget):
    """液态玻璃效果的Widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制半透明背景
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)

        # 背景色
        painter.fillPath(path, QColor(255, 255, 255, 180))

        # 边框高光
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        painter.drawPath(path)



class ThemeButton(QPushButton):
    """主题选择按钮"""
    def __init__(self, theme_name, color, parent=None):
        super().__init__(theme_name, parent)
        self.theme_name = theme_name
        self.color = color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(120, 40)
        self.setFont(QFont(get_system_font_family(), 9))

        # 缩放动画
        self._scale = 0.0
        self._scale_anim = QPropertyAnimation(self, b"scale", self)
        self._scale_anim.setDuration(300)
        self._scale_anim.setEasingCurve(QEasingCurve.OutBack)

    def get_scale(self):
        return self._scale

    def set_scale(self, v):
        self._scale = v
        self.update()

    scale = Property(float, get_scale, set_scale)

    def show_animated(self, delay=0):
        """带动画显示"""
        self._scale_anim.stop()
        self._scale_anim.setStartValue(0.0)
        self._scale_anim.setEndValue(1.0)
        if delay > 0:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(delay, self._scale_anim.start)
        else:
            self._scale_anim.start()

    def hide_animated(self):
        """带动画隐藏"""
        self._scale_anim.stop()
        self._scale_anim.setStartValue(1.0)
        self._scale_anim.setEndValue(0.0)
        self._scale_anim.start()

    def paintEvent(self, event):
        if self._scale < 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 应用缩放
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width() / 2, -self.height() / 2)

        # 绘制背景
        rect = self.rect()
        painter.setBrush(QColor(self.color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 8, 8)

        # 绘制文本
        painter.setPen(QColor("#ffffff"))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignCenter, self.theme_name)


class ThemeSelector(QWidget):
    """主题选择器弹出菜单"""
    theme_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.theme_buttons = []
        self._is_visible = False
        self._bg_opacity = 0.0

        # 背景透明度动画
        self._bg_anim = QPropertyAnimation(self, b"bgOpacity", self)
        self._bg_anim.setDuration(200)
        self._bg_anim.setEasingCurve(QEasingCurve.OutQuad)

    def get_bg_opacity(self):
        return self._bg_opacity

    def set_bg_opacity(self, v):
        self._bg_opacity = v
        self.update()

    bgOpacity = Property(float, get_bg_opacity, set_bg_opacity)

    def setup_themes(self, themes):
        """设置主题按钮"""
        from ui.themes import THEMES
        y_offset = 10

        for i, (name, theme_data) in enumerate(THEMES.items()):
            btn = ThemeButton(name, theme_data['accent'], self)
            btn.move(10, y_offset)
            btn.clicked.connect(lambda checked, n=name: self.on_theme_clicked(n))
            self.theme_buttons.append(btn)
            y_offset += 50

        self.setFixedSize(140, y_offset + 10)

    def on_theme_clicked(self, theme_name):
        """主题被点击"""
        self._is_visible = False  # 先设置为false防止focusOutEvent触发
        self.theme_selected.emit(theme_name)
        self.hide_animated()

    def show_at(self, pos):
        """在指定位置显示"""
        self.move(pos)
        self.show()
        self.activateWindow()
        self.setFocus()
        self._is_visible = True

        # 背景淡入
        self._bg_anim.stop()
        self._bg_anim.setStartValue(0.0)
        self._bg_anim.setEndValue(1.0)
        self._bg_anim.start()

        # 依次显示按钮
        for i, btn in enumerate(self.theme_buttons):
            btn.show_animated(delay=i * 50)

    def hide_animated(self):
        """带动画隐藏"""
        self._is_visible = False

        # 背景淡出
        self._bg_anim.stop()
        self._bg_anim.setStartValue(self._bg_opacity)
        self._bg_anim.setEndValue(0.0)
        self._bg_anim.finished.connect(self.hide)
        self._bg_anim.start()

        # 按钮隐藏
        for btn in reversed(self.theme_buttons):
            btn.hide_animated()

    def focusOutEvent(self, event):
        """失去焦点时关闭"""
        if self._is_visible:
            self.hide_animated()
        super().focusOutEvent(event)

    def paintEvent(self, event):
        """绘制半透明背景"""
        if self._bg_opacity < 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg_color = QColor(0, 0, 0, int(100 * self._bg_opacity))
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)


class CustomCheckBox(QCheckBox):
    """自定义复选框，手动绘制对钩"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("")

        # 动画属性
        self._check_progress = 0.0
        self._check_anim = QPropertyAnimation(self, b"checkProgress", self)
        self._check_anim.setDuration(200)
        self._check_anim.setEasingCurve(QEasingCurve.OutBack)

    def get_check_progress(self):
        return self._check_progress

    def set_check_progress(self, v):
        self._check_progress = v
        self.update()

    checkProgress = Property(float, get_check_progress, set_check_progress)

    def nextCheckState(self):
        super().nextCheckState()
        self._check_anim.stop()
        self._check_anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._check_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        # 绘制复选框
        box_size = 20
        box_y = (self.height() - box_size) // 2
        box_rect = QRect(0, box_y, box_size, box_size)

        # 背景色动画
        if self._check_progress > 0:
            bg_color = QColor(theme['accent'])
            border_color = QColor(theme['accent'])
        else:
            bg_color = QColor(theme['input_bg'])
            border_color = QColor(theme['border'])

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 2))
        painter.drawRoundedRect(box_rect, 4, 4)

        # 绘制对钩（带动画）
        if self._check_progress > 0.01:
            painter.setPen(QPen(QColor("white"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            offset_y = box_y
            # 对钩路径随进度绘制
            progress = self._check_progress
            painter.drawLine(5, 10 + offset_y, 5 + int(3 * progress), 10 + int(3 * progress) + offset_y)
            if progress > 0.5:
                sub_progress = (progress - 0.5) * 2
                painter.drawLine(8, 13 + offset_y, 8 + int(7 * sub_progress), 13 - int(7 * sub_progress) + offset_y)

        # 绘制文本
        if self.text():
            painter.setPen(QColor(theme['fg']))
            painter.setFont(self.font())
            text_rect = QRect(box_size + 8, 0, self.width() - box_size - 8, self.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


class AnimatedSidebarButton(QPushButton):
    def __init__(self, text, icon_emoji, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(55)
        self.icon_emoji = icon_emoji
        self.setFont(QFont(get_system_font_family(), 10, QFont.Bold))

        # 动画属性
        self._hover_progress = 0.0
        self._check_progress = 0.0

        # 悬停动画
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(250)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 选中动画
        self._check_anim = QPropertyAnimation(self, b"checkProgress", self)
        self._check_anim.setDuration(300)
        self._check_anim.setEasingCurve(QEasingCurve.OutBack)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, v):
        self._hover_progress = v
        self.update()

    def get_check_progress(self):
        return self._check_progress

    def set_check_progress(self, v):
        self._check_progress = v
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)
    checkProgress = Property(float, get_check_progress, set_check_progress)

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def checkStateSet(self):
        super().checkStateSet()
        self._check_anim.stop()
        self._check_anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._check_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        # 背景色混合
        bg_color = QColor(theme['accent'])
        if self._check_progress > 0:
            bg_color.setAlpha(int(40 * self._check_progress))
        else:
            alpha = int(20 * self._hover_progress)
            bg_color = QColor(theme['fg'])
            bg_color.setAlpha(alpha)

        # 绘制背景
        if self._check_progress > 0.01 or self._hover_progress > 0.01:
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(8, 4, -8, -4), 8, 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_color)
            painter.drawPath(path)

        # 选中指示条（带动画）
        if self._check_progress > 0.01:
            bar_height = 31 * self._check_progress
            bar_y = 12 + (31 - bar_height) / 2
            bar_rect = QRectF(8, bar_y, 4, bar_height)
            painter.setBrush(QColor(theme['accent']))
            painter.drawRoundedRect(bar_rect, 2, 2)

        # 文字颜色
        text_color = QColor(theme['accent']) if self._check_progress > 0.5 else QColor(theme['text_sec'])
        if self._check_progress < 0.5 and self._hover_progress > 0.5:
            text_color = QColor(theme['fg'])
        painter.setPen(text_color)

        # 图标
        font_icon = self.font()
        font_icon.setPointSize(14)
        painter.setFont(font_icon)
        painter.drawText(QRectF(20, 0, 40, 55), Qt.AlignCenter, self.icon_emoji)

        # 文本
        font_text = self.font()
        font_text.setPointSize(10)
        painter.setFont(font_text)
        painter.drawText(QRectF(60, 0, rect.width() - 60, 55), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class ModernButton(QPushButton):
    def __init__(self, text="", color_type="normal", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.color_type = color_type
        self.setMinimumHeight(36)
        self.setFont(QFont(get_system_font_family(), 9))

        # 点击动画
        self._press_scale = 1.0
        self._press_anim = QPropertyAnimation(self, b"pressScale", self)
        self._press_anim.setDuration(100)
        self._press_anim.setEasingCurve(QEasingCurve.OutQuad)

    def get_press_scale(self):
        return self._press_scale

    def set_press_scale(self, v):
        self._press_scale = v
        self.update()

    pressScale = Property(float, get_press_scale, set_press_scale)

    def mousePressEvent(self, event):
        self._press_anim.stop()
        self._press_anim.setStartValue(1.0)
        self._press_anim.setEndValue(0.95)
        self._press_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_anim.stop()
        self._press_anim.setStartValue(0.95)
        self._press_anim.setEndValue(1.0)
        self._press_anim.start()
        super().mouseReleaseEvent(event)

    def update_theme(self, theme):
        colors = {
            "primary": (theme['accent'], "#ffffff"),
            "danger": (theme['danger'], "#ffffff"),
            "normal": (theme['panel'], theme['fg'])
        }
        bg, fg = colors.get(self.color_type, colors["normal"])
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_hover'] if self.color_type == 'primary' else theme['border']};
            }}
            QPushButton:disabled {{
                background-color: {theme['bg']};
                color: {theme['text_sec']};
            }}
        """)


class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        from ui.themes import THEMES
        self.theme_data = THEMES["Light"]

    def update_theme(self, theme_data):
        self.theme_data = theme_data
        self.viewport().update()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            added = False
            existing_files = set([self.item(i).text() for i in range(self.count())])

            for url in e.mimeData().urls():
                path = url.toLocalFile()
                files_to_add = []

                if os.path.isfile(path):
                    files_to_add.append(path)
                elif os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        for file in files:
                            files_to_add.append(os.path.join(root, file))

                for f_path in files_to_add:
                    f_path = os.path.normpath(f_path)
                    if f_path not in existing_files:
                        self.addItem(f_path)
                        existing_files.add(f_path)
                        added = True

            if added and self.window():
                if hasattr(self.window(), 'check_constraints'):
                    self.window().check_constraints()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.viewport().rect().adjusted(10, 10, -10, -10)

            pen = QPen(QColor(self.theme_data["text_sec"]))
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, 8, 8)
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, "📂 拖拽文件或文件夹到此处")
