from PySide6.QtWidgets import QPushButton, QListWidget, QAbstractItemView, QCheckBox, QStyle, QStyleOptionButton, QWidget, QGraphicsBlurEffect, QScrollArea, QFrame, QVBoxLayout, QComboBox
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRectF, Property, QRect, QPoint, QParallelAnimationGroup, Signal
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen, QFont, QBrush, QLinearGradient
import os

from ui.platform_fonts import get_system_font_family


class DropDownComboBox(QComboBox):
    """下拉框 - 强制向下弹出并自定义绘制箭头"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self._arrow_color = QColor(100, 116, 139)  # 默认灰色

    def paintEvent(self, event):
        """自定义绘制，添加清晰的倒三角箭头"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取主题颜色
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]
        arrow_color = QColor(theme.get('text_sec', '#64748B'))

        # 绘制倒三角箭头 (位于右侧)
        arrow_x = self.width() - 20
        arrow_y = self.height() // 2

        # 三角形三个顶点
        painter.setPen(Qt.NoPen)
        painter.setBrush(arrow_color)

        # 绘制向下的三角形
        triangle = QPainterPath()
        triangle.moveTo(arrow_x - 5, arrow_y - 2)      # 左上
        triangle.lineTo(arrow_x + 5, arrow_y - 2)      # 右上
        triangle.lineTo(arrow_x, arrow_y + 4)          # 底部中心
        triangle.closeSubpath()
        painter.drawPath(triangle)

    def showPopup(self):
        """重写 showPopup，确保下拉框在下方显示"""
        super().showPopup()
        popup = self.findChild(QFrame)
        if popup:
            # 计算正确的位置
            combo_rect = self.rect()
            combo_pos = self.mapToGlobal(combo_rect.bottomLeft())
            # 设置在下方
            popup.move(combo_pos.x(), combo_pos.y() + 2)


class SmoothScrollArea(QScrollArea):
    """带自定义滚动条的可滚动区域"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 平滑滚动
        self.verticalScrollBar().setSingleStep(16)
        self.verticalScrollBar().setPageStep(100)

        # 滚动条样式 - 现代化设计
        self._scrollbar_opacity = 0.0
        self._scrollbar_anim = QPropertyAnimation(self, b"scrollbarOpacity", self)
        self._scrollbar_anim.setDuration(200)
        self._scrollbar_anim.setEasingCurve(QEasingCurve.OutQuad)

        # 滚动条可见性动画
        self._hide_timer = None

    def get_scrollbar_opacity(self):
        return self._scrollbar_opacity

    def set_scrollbar_opacity(self, v):
        self._scrollbar_opacity = v
        self.viewport().update()

    scrollbarOpacity = Property(float, get_scrollbar_opacity, set_scrollbar_opacity)

    def enterEvent(self, event):
        self._show_scrollbar()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hide_scrollbar_delayed()
        super().leaveEvent(event)

    def _show_scrollbar(self):
        if self._hide_timer:
            self._hide_timer.stop()
            self._hide_timer = None
        self._scrollbar_anim.stop()
        self._scrollbar_anim.setStartValue(self._scrollbar_opacity)
        self._scrollbar_anim.setEndValue(1.0)
        self._scrollbar_anim.start()

    def _hide_scrollbar_delayed(self):
        from PySide6.QtCore import QTimer
        if self._hide_timer:
            self._hide_timer.stop()
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_scrollbar)
        self._hide_timer.start(800)

    def _hide_scrollbar(self):
        self._scrollbar_anim.stop()
        self._scrollbar_anim.setStartValue(self._scrollbar_opacity)
        self._scrollbar_anim.setEndValue(0.0)
        self._scrollbar_anim.start()

    def update_theme(self, theme_data):
        """更新滚动条样式"""
        accent = theme_data.get('accent', '#007AFF')
        self.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 0, 0, 0.15);
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(0, 0, 0, 0.25);
            }}
            QScrollBar::handle:vertical:pressed {{
                background: rgba(0, 0, 0, 0.35);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)


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
        self.setMinimumHeight(32)

        # 动画属性
        self._check_progress = 1.0 if self.isChecked() else 0.0
        self._check_anim = QPropertyAnimation(self, b"checkProgress", self)
        self._check_anim.setDuration(180)
        self._check_anim.setEasingCurve(QEasingCurve.OutCubic)

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

        # 绘制复选框 - 添加左边距使其与输入框对齐
        box_size = 18
        box_x = 0
        box_y = (self.height() - box_size) // 2
        box_rect = QRect(box_x, box_y, box_size, box_size)

        # 背景色动画
        if self._check_progress > 0:
            bg_color = QColor(theme['accent'])
            border_color = QColor(theme['accent'])
        else:
            # 未选中状态使用柔和的背景和边框
            bg_color = QColor(255, 255, 255, 200)
            border_color = QColor(0, 0, 0, 60)

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(box_rect, 4, 4)

        # 绘制对钩（带动画）
        if self._check_progress > 0.01:
            painter.setPen(QPen(QColor("white"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            progress = self._check_progress

            # 基于 box_rect 计算对钩位置
            base_x = box_rect.left() + 5
            base_y = box_rect.top() + 9

            # 对钩左半部分
            painter.drawLine(base_x, base_y, base_x + int(3 * progress), base_y + int(3 * progress))

            # 对钩右半部分
            if progress > 0.5:
                sub_progress = (progress - 0.5) * 2
                painter.drawLine(base_x + 3, base_y + 3, base_x + 3 + int(7 * sub_progress), base_y + 3 - int(7 * sub_progress))

        # 绘制文本
        if self.text():
            painter.setPen(QColor(theme['fg']))
            font = self.font()
            font.setPointSize(12)
            painter.setFont(font)
            text_rect = QRect(box_x + box_size + 10, 0, self.width() - box_x - box_size - 10, self.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


class AnimatedSidebarButton(QPushButton):
    def __init__(self, text, icon_emoji, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        self.icon_emoji = icon_emoji
        self.setFont(QFont(get_system_font_family(), 10, QFont.Bold))

        # 动画属性
        self._hover_progress = 0.0
        self._check_progress = 0.0

        # 悬停动画
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(200)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 选中动画
        self._check_anim = QPropertyAnimation(self, b"checkProgress", self)
        self._check_anim.setDuration(250)
        self._check_anim.setEasingCurve(QEasingCurve.OutCubic)

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
        if self._check_progress > 0:
            # 选中状态
            bg_color = QColor(theme['accent'])
            bg_color.setAlpha(int(15 * self._check_progress))
            bg_brush = QBrush(bg_color)
        else:
            # 悬停状态
            bg_color = QColor(0, 0, 0)
            bg_color.setAlpha(int(8 * self._hover_progress))
            bg_brush = QBrush(bg_color)

        # 绘制背景
        if self._check_progress > 0.01 or self._hover_progress > 0.01:
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(8, 4, -8, -4), 8, 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_brush)
            painter.drawPath(path)

        # 选中指示条（左侧竖条）
        if self._check_progress > 0.01:
            bar_height = 24 * self._check_progress
            bar_y = 12 + (24 - bar_height) / 2
            bar_rect = QRectF(6, bar_y, 3, bar_height)
            painter.setBrush(QColor(theme['accent']))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_rect, 1.5, 1.5)

        # 文字颜色
        text_color = QColor(theme['accent']) if self._check_progress > 0.5 else QColor(theme['text_sec'])
        if self._check_progress < 0.5 and self._hover_progress > 0.5:
            text_color = QColor(theme['fg'])
        painter.setPen(text_color)

        # 图标
        font_icon = self.font()
        font_icon.setPointSize(14)
        painter.setFont(font_icon)
        painter.drawText(QRectF(16, 0, 36, 48), Qt.AlignCenter, self.icon_emoji)

        # 文本
        font_text = self.font()
        font_text.setPointSize(11)
        font_text.setWeight(QFont.DemiBold)
        painter.setFont(font_text)
        painter.drawText(QRectF(52, 0, rect.width() - 52, 48), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class ModernButton(QPushButton):
    def __init__(self, text="", color_type="normal", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.color_type = color_type
        self.setFont(QFont(get_system_font_family(), 10))

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
            "normal": ("rgba(255, 255, 255, 0.08)", theme['fg'])
        }
        bg, fg = colors.get(self.color_type, colors["normal"])

        if self.color_type == "primary":
            style = f"""
                QPushButton {{
                    background: {theme['accent']};
                    color: {fg};
                    border: none;
                    border-radius: 10px;
                    padding: 0 20px;
                    font-weight: 600;
                    font-size: 13px;
                    letter-spacing: 0.3px;
                }}
                QPushButton:hover {{
                    background: {theme['accent_hover']};
                }}
                QPushButton:pressed {{
                    background: {theme['accent']};
                }}
                QPushButton:disabled {{
                    background: rgba(0, 0, 0, 0.1);
                    color: rgba(0, 0, 0, 0.3);
                }}
            """
        elif self.color_type == "danger":
            style = f"""
                QPushButton {{
                    background: {theme['danger']};
                    color: {fg};
                    border: none;
                    border-radius: 10px;
                    padding: 0 20px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: #B91C1C;
                }}
                QPushButton:pressed {{
                    background: {theme['danger']};
                }}
                QPushButton:disabled {{
                    background: rgba(0, 0, 0, 0.1);
                    color: rgba(0, 0, 0, 0.3);
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background: rgba(0, 0, 0, 0.04);
                    color: {theme['fg']};
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                    padding: 0 16px;
                    font-weight: 500;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: rgba(0, 0, 0, 0.08);
                    border: 1px solid rgba(0, 0, 0, 0.15);
                }}
                QPushButton:pressed {{
                    background: rgba(0, 0, 0, 0.12);
                }}
                QPushButton:disabled {{
                    background: rgba(0, 0, 0, 0.02);
                    color: rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(0, 0, 0, 0.05);
                }}
            """
        self.setStyleSheet(style)


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
            rect = self.viewport().rect().adjusted(16, 16, -16, -16)

            # 虚线边框
            pen = QPen(QColor(self.theme_data["text_sec"]))
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1.5)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, 12, 12)

            # 提示文字
            painter.setPen(QColor(self.theme_data["text_sec"]))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, "📂 拖拽文件或文件夹到此处")
