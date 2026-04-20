# -*- coding: utf-8 -*-
"""
Encryption Studio - UI 组件模块
================================

本模块包含应用程序中所有自定义 UI 组件，遵循 macOS Sonoma/Sequoia 视觉规范。

主要组件:
---------
输入控件:
    - DropDownComboBox: 自定义下拉框，支持向下弹出和自定义箭头绘制
    - CustomCheckBox: 毛玻璃风格复选框，带动画效果
    - GlassInputField: 玻璃质感输入框

导航组件:
    - AnimatedSidebarButton: 侧边栏导航按钮，带胶囊选中态动画
    - ThemeSelector: 主题选择器弹出菜单

按钮组件:
    - ModernButton: Apple 风格主按钮，支持渐变和内发光
    - SystemSwitchButton: 系统切换按钮，带颜色变化和装饰花纹

容器组件:
    - SmoothScrollArea: 平滑滚动区域，带自定义滚动条
    - GlassCard: 玻璃质感卡片容器
    - GlassSectionCard: 配置面板 Section 卡片
    - ConfigPanelCard: 右侧配置面板卡片

进度组件:
    - GlassProgressBar: 玻璃质感进度条，带流光动画和发光效果

其他:
    - DragDropListWidget: 拖拽文件列表组件
    - ThemeButton: 主题选择按钮（内部使用）
    - GlassWidget: 液态玻璃效果 Widget

设计规范:
所有组件遵循 macOS Human Interface Guidelines，使用毛玻璃效果、
柔和阴影、高光边缘等视觉元素，保证跨平台一致性。
"""

from PySide6.QtWidgets import (QPushButton, QListWidget, QAbstractItemView, QCheckBox,
                                 QStyle, QStyleOptionButton, QWidget, QGraphicsBlurEffect,
                                 QScrollArea, QFrame, QVBoxLayout, QComboBox, QGraphicsDropShadowEffect,
                                 QGroupBox, QLabel, QLineEdit, QHBoxLayout)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRectF, Property, QRect, QPoint, QParallelAnimationGroup, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen, QFont, QBrush, QLinearGradient, QFontMetrics, QGradient
import os

from ui.platform_fonts import get_system_font_family


class DropDownComboBox(QComboBox):
    """
    下拉框组件 - 强制向下弹出并自定义绘制箭头

    继承自 QComboBox，重写弹出位置和箭头绘制逻辑，
    确保下拉列表始终向下弹出，并使用自定义的三角形箭头。

    特点:
        - 固定最小高度 44px
        - 自定义倒三角箭头指示器
        - 下拉列表向下弹出
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(44)
        self._arrow_color = QColor(100, 116, 139)

    def paintEvent(self, event):
        """自定义绘制，添加清晰的倒三角箭头"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]
        arrow_color = QColor(theme.get('fg_secondary', '#64748B'))

        # 绘制倒三角箭头
        arrow_x = self.width() - 20
        arrow_y = self.height() // 2

        painter.setPen(Qt.NoPen)
        painter.setBrush(arrow_color)

        triangle = QPainterPath()
        triangle.moveTo(arrow_x - 5, arrow_y - 2)
        triangle.lineTo(arrow_x + 5, arrow_y - 2)
        triangle.lineTo(arrow_x, arrow_y + 4)
        triangle.closeSubpath()
        painter.drawPath(triangle)

    def showPopup(self):
        """重写 showPopup，确保下拉框在下方显示"""
        super().showPopup()
        popup = self.findChild(QFrame)
        if popup:
            combo_rect = self.rect()
            combo_pos = self.mapToGlobal(combo_rect.bottomLeft())
            popup.move(combo_pos.x(), combo_pos.y() + 2)


class SmoothScrollArea(QScrollArea):
    """
    平滑滚动区域 - 毛玻璃风格

    自定义 QScrollArea，提供以下特性：
        - 淡入淡出的滚动条动画
        - 鼠标离开后延迟隐藏滚动条
        - 透明背景以支持毛玻璃效果
        - 自定义滚动条样式

    使用方式:
        scroll_area = SmoothScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.update_theme(theme_data)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 平滑滚动配置
        self.verticalScrollBar().setSingleStep(16)
        self.verticalScrollBar().setPageStep(100)

        # 滚动条可见性动画
        self._scrollbar_opacity = 0.0
        self._scrollbar_anim = QPropertyAnimation(self, b"scrollbarOpacity", self)
        self._scrollbar_anim.setDuration(200)
        self._scrollbar_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._hide_timer = None

    def get_scrollbar_opacity(self):
        """获取滚动条透明度（动画属性）"""
        return self._scrollbar_opacity

    def set_scrollbar_opacity(self, v):
        """设置滚动条透明度（动画属性）"""
        self._scrollbar_opacity = v
        self.viewport().update()

    scrollbarOpacity = Property(float, get_scrollbar_opacity, set_scrollbar_opacity)

    def enterEvent(self, event):
        """鼠标进入时显示滚动条"""
        self._show_scrollbar()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开时延迟隐藏滚动条"""
        self._hide_scrollbar_delayed()
        super().leaveEvent(event)

    def _show_scrollbar(self):
        """播放滚动条淡入动画"""
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
        """更新滚动条样式 - 毛玻璃风格"""
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
                width: 6px;
                margin: 4px 2px 4px 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 0, 0, 0.12);
                min-height: 30px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(0, 0, 0, 0.20);
            }}
            QScrollBar::handle:vertical:pressed {{
                background: rgba(0, 0, 0, 0.28);
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


class GlassSectionCard(QFrame):
    """
    玻璃质感 Section 卡片组件
    DOM 结构: Glass容器 -> 内部Section卡片 -> 表单元素
    严格遵循 macOS Sonoma/Sequoia 视觉规范
    """
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassSectionCard")
        self._title = title
        self._theme_data = None

        # 主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 标题区域
        self._title_bar = QWidget()
        self._title_bar.setObjectName("CardTitleBar")
        self._title_layout = QHBoxLayout(self._title_bar)
        self._title_layout.setContentsMargins(18, 16, 18, 12)
        self._title_layout.setSpacing(8)

        # 标题图标 + 文字
        self._title_label = QLabel(title)
        self._title_label.setObjectName("CardTitle")
        self._title_layout.addWidget(self._title_label)
        self._title_layout.addStretch()

        self._main_layout.addWidget(self._title_bar)

        # 内容区域
        self._content = QWidget()
        self._content.setObjectName("CardContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(18, 4, 18, 18)
        self._content_layout.setSpacing(14)

        self._main_layout.addWidget(self._content)

    def content_layout(self):
        """返回内容区域的布局，供外部添加控件"""
        return self._content_layout

    def update_theme(self, theme_data):
        """更新主题样式"""
        self._theme_data = theme_data


class GlassWidget(QWidget):
    """液态玻璃效果的Widget - 带高光边缘"""
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
    """主题选择按钮 - 毛玻璃风格"""
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
    """主题选择器弹出菜单 - 毛玻璃风格"""
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
        self._is_visible = False
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
    """
    自定义复选框 - 毛玻璃风格

    继承自 QCheckBox，提供以下特性：
        - 自定义绘制，不使用系统默认样式
        - 选中时显示蓝色渐变背景
        - 未选中时显示半透明玻璃效果
        - 勾选动画：从左到右逐渐绘制对钩

    视觉规范:
        - 复选框尺寸: 20x20px
        - 圆角: 6px
        - 选中色: accent 渐变
        - 未选中色: rgba(255,255,255,180)
    """
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("")  # 清除默认样式
        self.setMinimumHeight(36)

        # 动画属性：用于平滑过渡勾选状态
        self._check_progress = 1.0 if self.isChecked() else 0.0
        self._check_anim = QPropertyAnimation(self, b"checkProgress", self)
        self._check_anim.setDuration(180)
        self._check_anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_check_progress(self):
        """获取勾选进度（动画属性，0.0-1.0）"""
        return self._check_progress

    def set_check_progress(self, v):
        """设置勾选进度（动画属性）"""
        self._check_progress = v
        self.update()

    checkProgress = Property(float, get_check_progress, set_check_progress)

    def nextCheckState(self):
        """切换选中状态时触发动画"""
        super().nextCheckState()
        self._check_anim.stop()
        self._check_anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._check_anim.start()

    def paintEvent(self, event):
        """自定义绘制复选框和文字"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        # 复选框尺寸和位置
        box_size = 20
        box_x = 2
        box_y = (self.height() - box_size) // 2
        box_rect = QRect(box_x, box_y, box_size, box_size)

        # 绘制背景 - 毛玻璃效果
        if self._check_progress > 0:
            # 选中状态 - 渐变蓝色
            gradient = QLinearGradient(box_rect.topLeft(), box_rect.bottomLeft())
            accent = QColor(theme['accent'])
            gradient.setColorAt(0, accent.lighter(110))
            gradient.setColorAt(1, accent)
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
        else:
            # 未选中状态 - 半透明玻璃
            bg_color = QColor(255, 255, 255, 180)
            border_color = QColor(0, 0, 0, 40)
            painter.setBrush(bg_color)
            painter.setPen(QPen(border_color, 1.2))

        painter.drawRoundedRect(box_rect, 6, 6)

        # 绘制对钩（带动画）
        if self._check_progress > 0.01:
            painter.setPen(QPen(QColor("white"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            progress = self._check_progress

            base_x = box_rect.left() + 5
            base_y = box_rect.top() + 10

            # 对钩左半部分
            painter.drawLine(base_x, base_y, base_x + int(3.5 * progress), base_y + int(3.5 * progress))

            # 对钩右半部分
            if progress > 0.5:
                sub_progress = (progress - 0.5) * 2
                painter.drawLine(base_x + 3.5, base_y + 3.5, base_x + 3.5 + int(7.5 * sub_progress), base_y + 3.5 - int(7.5 * sub_progress))

        # 绘制文本
        if self.text():
            painter.setPen(QColor(theme['fg']))
            font = self.font()
            font.setPointSize(12)
            font.setWeight(QFont.Medium)
            painter.setFont(font)
            text_rect = QRect(box_x + box_size + 12, 0, self.width() - box_x - box_size - 12, self.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


class AnimatedSidebarButton(QPushButton):
    """
    Apple 风格侧边栏导航按钮 - 毛玻璃胶囊选中态

    用于侧边栏导航，提供以下特性：
        - 可选中（checkable）且互斥（autoExclusive）
        - 悬停动画：鼠标悬停时背景渐变
        - 选中动画：选中时显示蓝色半透明胶囊背景
        - 顶部高光：模拟玻璃厚度的顶部高光线条
        - 图标 + 文字组合显示

    视觉规范:
        - 选中背景: rgba(0,122,255,0.15) - 半透明蓝色
        - 选中文字/图标: #007AFF
        - 圆角: 8px（胶囊形状）
        - 固定高度: 48px
    """

    def __init__(self, text, icon_emoji, parent=None):
        """
        初始化侧边栏按钮

        参数:
            text: 按钮显示文本
            icon_emoji: 图标 emoji 字符，如 "🔒"
            parent: 父组件
        """
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        self.icon_emoji = icon_emoji
        self.setFont(QFont(get_system_font_family(), 11, QFont.DemiBold))

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
        """获取悬停进度（动画属性）"""
        return self._hover_progress

    def set_hover_progress(self, v):
        """设置悬停进度（动画属性）"""
        self._hover_progress = v
        self.update()

    def get_check_progress(self):
        """获取选中进度（动画属性）"""
        return self._check_progress

    def set_check_progress(self, v):
        """设置选中进度（动画属性）"""
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

        # === 胶囊背景区域 ===
        capsule_rect = rect.adjusted(8, 4, -8, -4)
        radius = 8  # 圆角 8px，无阴影

        # 1. 悬停状态 - 极浅的灰色背景
        if self._hover_progress > 0.01 and self._check_progress < 0.01:
            hover_bg = QColor(0, 0, 0, int(12 * self._hover_progress))
            painter.setBrush(hover_bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(capsule_rect, radius, radius)

        # 2. 选中状态 - 使用主题色
        if self._check_progress > 0.01:
            # 从主题获取 accent 颜色
            accent_hex = theme.get('accent', '#6366F1')
            accent_color = QColor(accent_hex)
            active_bg = QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(38 * self._check_progress))
            painter.setBrush(active_bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(capsule_rect, radius, radius)

        # === 文字与图标 ===
        # 图标颜色 - 选中时使用主题色
        if self._check_progress > 0.5:
            accent_hex = theme.get('accent', '#6366F1')
            icon_color = QColor(accent_hex)
        else:
            icon_color = QColor(theme.get('fg_secondary', 'rgba(0, 0, 0, 0.50)'))
        painter.setPen(icon_color)

        font_icon = self.font()
        font_icon.setPointSize(17)
        painter.setFont(font_icon)
        painter.drawText(QRectF(16, 0, 32, 48), Qt.AlignCenter, self.icon_emoji)

        # 文本颜色
        if self._check_progress > 0.5:
            accent_hex = theme.get('accent', '#6366F1')
            text_color = QColor(accent_hex)
        else:
            text_color = QColor(theme.get('fg', '#1D1D1F'))
        painter.setPen(text_color)
        font_text = self.font()
        font_text.setPointSize(12)
        font_text.setWeight(QFont.DemiBold)
        painter.setFont(font_text)
        painter.drawText(QRectF(48, 0, rect.width() - 48, 48), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class ModernButton(QPushButton):
    """
    Apple 风格主按钮 - Vibrant Blue 渐变 + 内发光

    通用按钮组件，支持三种样式：
        - primary: 主按钮，蓝色渐变背景，用于主要操作
        - danger: 危险按钮，红色背景，用于删除等危险操作
        - normal: 普通按钮，玻璃质感背景，用于次要操作

    特性:
        - 点击动画：按下时微缩放，释放时恢复
        - 主题支持：通过 update_theme() 方法应用主题色
        - Hover 效果：鼠标悬停时颜色变化

    视觉规范:
        - 主按钮渐变: #2A85FF → #0062FF
        - 圆角: 8px
        - 最小高度: 40-48px（根据类型）
    """

    def __init__(self, text="", color_type="normal", parent=None):
        """
        初始化按钮

        参数:
            text: 按钮显示文本
            color_type: 按钮类型 ("primary", "danger", "normal")
            parent: 父组件
        """
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.color_type = color_type
        self.setFont(QFont(get_system_font_family(), 11, QFont.DemiBold))

        # 点击动画属性
        self._press_scale = 1.0
        self._press_anim = QPropertyAnimation(self, b"pressScale", self)
        self._press_anim.setDuration(100)
        self._press_anim.setEasingCurve(QEasingCurve.OutQuad)

    def get_press_scale(self):
        """获取按下缩放比例（动画属性）"""
        return self._press_scale

    def set_press_scale(self, v):
        """设置按下缩放比例（动画属性）"""
        self._press_scale = v
        self.update()

    pressScale = Property(float, get_press_scale, set_press_scale)

    def mousePressEvent(self, event):
        self._press_anim.stop()
        self._press_anim.setStartValue(1.0)
        self._press_anim.setEndValue(0.97)
        self._press_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_anim.stop()
        self._press_anim.setStartValue(0.97)
        self._press_anim.setEndValue(1.0)
        self._press_anim.start()
        super().mouseReleaseEvent(event)

    def update_theme(self, theme):
        if self.color_type == "primary":
            # Apple Vibrant Blue 渐变 - 内发光效果
            style = f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2A85FF, stop:1 #0062FF);
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 0 28px;
                    font-weight: 600;
                    font-size: 14px;
                    letter-spacing: 0.3px;
                    min-height: 48px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4296FF, stop:1 #0070FF);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1A75FF, stop:1 #0055EE);
                }}
                QPushButton:disabled {{
                    background: rgba(0, 0, 0, 0.08);
                    color: rgba(0, 0, 0, 0.30);
                }}
            """
        elif self.color_type == "danger":
            style = f"""
                QPushButton {{
                    background: {theme.get('danger', '#FF3B30')};
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 0 24px;
                    font-weight: 600;
                    font-size: 14px;
                    min-height: 44px;
                }}
                QPushButton:hover {{
                    background: {theme.get('danger_hover', '#FF6259')};
                }}
                QPushButton:pressed {{
                    background: #E52E24;
                }}
                QPushButton:disabled {{
                    background: rgba(0, 0, 0, 0.08);
                    color: rgba(0, 0, 0, 0.30);
                }}
            """
        else:
            # 玻璃质感普通按钮 - 内嵌式
            style = f"""
                QPushButton {{
                    background: rgba(0, 0, 0, 0.03);
                    color: {theme.get('fg', '#1D1D1F')};
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    border-radius: 6px;
                    padding: 0 20px;
                    font-weight: 500;
                    font-size: 13px;
                    min-height: 40px;
                }}
                QPushButton:hover {{
                    background: rgba(0, 0, 0, 0.06);
                    border: 1px solid rgba(0, 0, 0, 0.10);
                }}
                QPushButton:pressed {{
                    background: rgba(0, 0, 0, 0.08);
                }}
                QPushButton:disabled {{
                    background: rgba(0, 0, 0, 0.02);
                    color: {theme.get('fg_tertiary', 'rgba(0, 0, 0, 0.35)')};
                }}
            """
        self.setStyleSheet(style)


class DragDropListWidget(QListWidget):
    """
    拖拽文件列表组件 - 毛玻璃风格虚线框

    继承自 QListWidget，用于显示待处理的文件队列。
    支持拖拽文件/文件夹添加到列表。

    特性:
        - 拖拽文件/文件夹自动识别
        - 空列表时显示虚线框占位提示
        - 拖拽悬停时高亮效果
        - 递归扫描文件夹中的所有文件

    视觉规范:
        - 虚线边框: 1.5px dashed rgba(0,0,0,0.15)
        - 悬停背景: rgba(255,255,255,0.5)
        - 悬停边框: rgba(0,122,255,0.35)
        - 圆角: 12px
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        from ui.themes import THEMES
        self.theme_data = THEMES["Light"]
        self._drag_hover = False

    def update_theme(self, theme_data):
        self.theme_data = theme_data
        self.viewport().update()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self._drag_hover = True
            self.viewport().update()
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._drag_hover = False
        self.viewport().update()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self._drag_hover = False
        self.viewport().update()

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
            rect = self.viewport().rect().adjusted(20, 20, -20, -20)

            # 拖拽悬停时的背景 - Hover 时使用主题色
            if self._drag_hover:
                hover_bg = QColor(255, 255, 255, int(255 * 0.5))
                painter.fillRect(rect, hover_bg)
                # 使用主题的 accent 颜色
                accent_hex = self.theme_data.get('accent', '#6366F1')
                accent_color = QColor(accent_hex)
                pen = QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(255 * 0.35)))
            else:
                # 正常状态背景 rgba(255,255,255, 0.3)
                normal_bg = QColor(255, 255, 255, int(255 * 0.3))
                painter.fillRect(rect, normal_bg)
                # 虚线要细且柔和 border: 1.5px dashed rgba(0,0,0, 0.15)
                pen = QPen(QColor(0, 0, 0, int(255 * 0.15)))

            pen.setStyle(Qt.DashLine)
            pen.setWidth(1.5)
            pen.setDashPattern([6, 4])
            painter.setPen(pen)
            painter.drawRoundedRect(rect, 12, 12)

            # 提示文字 - 更精致的排版
            painter.setPen(QColor(self.theme_data.get('fg_secondary', 'rgba(0, 0, 0, 0.50)')))
            font = QFont(get_system_font_family(), 13)
            font.setWeight(QFont.Medium)
            painter.setFont(font)

            # 图标 + 文字
            icon_rect = QRectF(rect.center().x() - 20, rect.center().y() - 40, 40, 40)
            painter.setPen(QColor(self.theme_data.get('accent', '#6366F1')))
            font_icon = QFont()
            font_icon.setPointSize(28)
            painter.setFont(font_icon)
            painter.drawText(icon_rect, Qt.AlignCenter, "📂")

            # 主文字
            painter.setPen(QColor(self.theme_data.get('fg_secondary', 'rgba(0, 0, 0, 0.50)')))
            font_text = QFont(get_system_font_family(), 13)
            font_text.setWeight(QFont.Medium)
            painter.setFont(font_text)
            text_rect = QRectF(rect.left(), rect.center().y() + 5, rect.width(), 30)
            painter.drawText(text_rect, Qt.AlignCenter, "拖拽文件或文件夹到此处")

            # 副文字
            font_sub = QFont(get_system_font_family(), 11)
            font_sub.setWeight(QFont.Normal)
            painter.setFont(font_sub)
            painter.setPen(QColor(self.theme_data.get('fg_tertiary', 'rgba(0, 0, 0, 0.35)')))
            sub_rect = QRectF(rect.left(), rect.center().y() + 30, rect.width(), 25)
            painter.drawText(sub_rect, Qt.AlignCenter, "支持批量添加，自动识别文件类型")


class GlassInputField(QLineEdit):
    """玻璃质感输入框 - 内嵌式效果"""
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(44)
        self.setAttribute(Qt.WA_MacShowFocusRect, 0)  # macOS: 移除默认焦点框

    def paintEvent(self, event):
        # 自定义绘制内阴影效果
        super().paintEvent(event)


class GlassCard(QFrame):
    """
    玻璃质感卡片容器
    实现背景渐变 + 高光边缘 + 柔和阴影
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self._theme_data = None

    def paintEvent(self, event):
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())
        radius = 12.0

        # 1. 绘制柔和阴影 (多层弥散阴影)
        # box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.05), 0 0 1px 0 rgba(0, 0, 0, 0.1)
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(rect.adjusted(0, 2, 0, 2), radius, radius)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 12))  # 0.05 * 255 ≈ 12
        painter.drawPath(shadow_path)

        # 2. 绘制渐变背景
        # background: linear-gradient(135deg, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0.4) 100%)
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, int(255 * 0.70)))
        gradient.setColorAt(1, QColor(255, 255, 255, int(255 * 0.40)))

        bg_path = QPainterPath()
        bg_path.addRoundedRect(rect, radius, radius)
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPath(bg_path)

        # 3. 绘制高光边缘 (1px 描边模拟玻璃切面)
        # border: 1px solid rgba(255, 255, 255, 0.6)
        painter.setPen(QPen(QColor(255, 255, 255, int(255 * 0.60)), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # 4. 底部边缘 (光线自上而下的衰减)
        # border-bottom: 1px solid rgba(255, 255, 255, 0.3)
        bottom_line = QPainterPath()
        bottom_y = rect.bottom() - 1
        bottom_line.moveTo(rect.left() + radius, bottom_y)
        bottom_line.lineTo(rect.right() - radius, bottom_y)
        painter.setPen(QPen(QColor(255, 255, 255, int(255 * 0.30)), 1.0))
        painter.drawPath(bottom_line)


class ConfigPanelCard(QFrame):
    """
    右侧配置面板的 Section 卡片
    严格遵循 macOS Sonoma/Sequoia 视觉规范
    """
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ConfigPanelCard")
        self._title = title
        self._theme_data = None

        # 主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 标题区域
        self._title_bar = QWidget()
        self._title_bar.setObjectName("CardTitleBar")
        self._title_bar.setFixedHeight(44)
        self._title_layout = QHBoxLayout(self._title_bar)
        self._title_layout.setContentsMargins(16, 0, 16, 0)
        self._title_layout.setSpacing(8)

        # 标题图标 + 文字
        self._title_label = QLabel(title)
        self._title_label.setObjectName("CardTitleLabel")
        self._title_layout.addWidget(self._title_label)
        self._title_layout.addStretch()

        self._main_layout.addWidget(self._title_bar)

        # 内容区域
        self._content = QWidget()
        self._content.setObjectName("CardContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(16, 8, 16, 16)
        self._content_layout.setSpacing(12)

        self._main_layout.addWidget(self._content)

    def content_layout(self):
        """返回内容区域的布局，供外部添加控件"""
        return self._content_layout

    def paintEvent(self, event):
        """自定义绘制 - 内嵌式玻璃质感"""
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())
        radius = 12.0

        # 绘制内嵌式玻璃背景
        # background: rgba(0, 0, 0, 0.03)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, int(255 * 0.03)))
        painter.drawRoundedRect(rect, radius, radius)

        # 内阴影效果
        # box-shadow: inset 0 1px 2px rgba(0,0,0,0.04)
        # 注: Qt 不直接支持 inset shadow，通过绘制边缘线模拟
        painter.setPen(QPen(QColor(0, 0, 0, int(255 * 0.04)), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)


class SystemSwitchButton(QPushButton):
    """
    系统切换按钮 - 带状态变化和装饰效果
    macOS 风格，选中状态有颜色变化和装饰花纹
    """
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont(get_system_font_family(), 10, QFont.DemiBold))
        self._is_new_system = False  # False = 老系统, True = 新系统
        self._hover_progress = 0.0
        self._switch_progress = 0.0  # 0.0 = 老系统, 1.0 = 新系统

        # 悬停动画
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(200)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 切换动画
        self._switch_anim = QPropertyAnimation(self, b"switchProgress", self)
        self._switch_anim.setDuration(300)
        self._switch_anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, v):
        self._hover_progress = v
        self.update()

    def get_switch_progress(self):
        return self._switch_progress

    def set_switch_progress(self, v):
        self._switch_progress = v
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)
    switchProgress = Property(float, get_switch_progress, set_switch_progress)

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

    def set_new_system(self, is_new: bool):
        """设置当前系统状态"""
        self._is_new_system = is_new
        self._switch_anim.stop()
        self._switch_anim.setEndValue(1.0 if is_new else 0.0)
        self._switch_anim.start()
        if is_new:
            self.setText("← 切换到老系统")
        else:
            self.setText("切换到新系统 →")

    def paintEvent(self, event):
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())
        radius = 6.0

        # === 根据切换进度选择渐变颜色 ===
        # 老系统 (0.0): 紫蓝色渐变 #818CF8 → #6366F1
        # 新系统 (1.0): 粉色渐变 #F472B6 → #EC4899 (更鲜明的对比)
        progress = self._switch_progress

        # 插值计算颜色 - 统一使用主题色
        old_start = QColor(129, 140, 248)   # #818CF8 (紫蓝)
        old_end = QColor(99, 102, 241)       # #6366F1
        new_start = QColor(244, 114, 182)   # #F472B6 (粉色)
        new_end = QColor(236, 72, 153)      # #EC4899

        start_color = QColor(
            int(old_start.red() * (1 - progress) + new_start.red() * progress),
            int(old_start.green() * (1 - progress) + new_start.green() * progress),
            int(old_start.blue() * (1 - progress) + new_start.blue() * progress)
        )
        end_color = QColor(
            int(old_end.red() * (1 - progress) + new_end.red() * progress),
            int(old_end.green() * (1 - progress) + new_end.green() * progress),
            int(old_end.blue() * (1 - progress) + new_end.blue() * progress)
        )

        # 绘制渐变背景
        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, start_color)
        gradient.setColorAt(1, end_color)

        # 悬停时稍微提亮
        if self._hover_progress > 0.01:
            hover_overlay = QColor(255, 255, 255, int(20 * self._hover_progress))
            painter.setBrush(hover_overlay)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, radius, radius)

        # 主背景
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        # === 绘制装饰花纹 (选中新系统时) ===
        if progress > 0.01:
            painter.setPen(QPen(QColor(255, 255, 255, int(40 * progress)), 1.0))
            painter.setBrush(Qt.NoBrush)

            # 左上角装饰
            deco_offset = 4
            painter.drawLine(
                QPointF(rect.left() + deco_offset, rect.top() + 8 * progress),
                QPointF(rect.left() + deco_offset + 6 * progress, rect.top() + deco_offset)
            )
            # 右下角装饰
            painter.drawLine(
                QPointF(rect.right() - deco_offset, rect.bottom() - 8 * progress - deco_offset),
                QPointF(rect.right() - deco_offset - 6 * progress, rect.bottom() - deco_offset)
            )

        # === 内发光效果 ===
        inner_glow = QLinearGradient(0, 0, 0, 3)
        inner_glow.setColorAt(0, QColor(255, 255, 255, 80))
        inner_glow.setColorAt(1, QColor(255, 255, 255, 0))
        glow_rect = QRectF(rect.left() + 1, rect.top() + 1, rect.width() - 2, 8)
        painter.setBrush(inner_glow)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(glow_rect, radius - 1, radius - 1)

        # === 绘制文字 ===
        painter.setPen(QColor(255, 255, 255))
        font = self.font()
        font.setPointSize(10)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())


class GlassProgressBar(QWidget):
    """
    玻璃质感进度条 - macOS 风格
    特点：毛玻璃背景 + 渐变填充 + 发光效果 + 流动动画
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._min = 0
        self._max = 100
        self._shimmer_offset = 0.0  # 流光动画偏移
        self._glow_intensity = 0.0  # 发光强度

        self.setFixedHeight(6)  # 进度条高度

        # 流光动画
        self._shimmer_anim = QPropertyAnimation(self, b"shimmerOffset", self)
        self._shimmer_anim.setDuration(1500)
        self._shimmer_anim.setStartValue(0.0)
        self._shimmer_anim.setEndValue(1.0)
        self._shimmer_anim.setLoopCount(-1)  # 无限循环
        self._shimmer_anim.setEasingCurve(QEasingCurve.Linear)

        # 发光动画 (用于进度变化时的高亮)
        self._glow_anim = QPropertyAnimation(self, b"glowIntensity", self)
        self._glow_anim.setDuration(300)
        self._glow_anim.setEasingCurve(QEasingCurve.OutQuad)

    def get_shimmer_offset(self):
        return self._shimmer_offset

    def set_shimmer_offset(self, v):
        self._shimmer_offset = v
        self.update()

    def get_glow_intensity(self):
        return self._glow_intensity

    def set_glow_intensity(self, v):
        self._glow_intensity = v
        self.update()

    shimmerOffset = Property(float, get_shimmer_offset, set_shimmer_offset)
    glowIntensity = Property(float, get_glow_intensity, set_glow_intensity)

    def setValue(self, value):
        """设置进度值"""
        old_value = self._value
        self._value = max(self._min, min(value, self._max))

        # 进度变化时触发发光效果
        if self._value != old_value:
            self._glow_anim.stop()
            self._glow_anim.setStartValue(1.0)
            self._glow_anim.setEndValue(0.0)
            self._glow_anim.start()

        self.update()

    def value(self):
        return self._value

    def setMinimum(self, min_val):
        self._min = min_val

    def setMaximum(self, max_val):
        self._max = max_val

    def minimum(self):
        return self._min

    def maximum(self):
        return self._max

    def start_shimmer(self):
        """开始流光动画"""
        self._shimmer_anim.start()

    def stop_shimmer(self):
        """停止流光动画"""
        self._shimmer_anim.stop()
        self._shimmer_offset = 0.0
        self.update()

    def reset(self):
        """重置进度"""
        self._value = self._min
        self._glow_anim.stop()
        self._glow_intensity = 0.0
        self.stop_shimmer()
        self.update()

    def paintEvent(self, event):
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())
        radius = 3.0

        # === 1. 绘制背景轨道 (毛玻璃) ===
        # background: rgba(0, 0, 0, 0.06)
        track_path = QPainterPath()
        track_path.addRoundedRect(rect, radius, radius)
        painter.setBrush(QColor(0, 0, 0, 15))  # rgba(0,0,0,0.06)
        painter.setPen(Qt.NoPen)
        painter.drawPath(track_path)

        # === 2. 绘制进度填充 ===
        if self._max > self._min:
            progress = (self._value - self._min) / (self._max - self._min)
            if progress > 0:
                fill_width = rect.width() * progress
                fill_rect = QRectF(rect.left(), rect.top(), fill_width, rect.height())

                # 渐变填充
                fill_gradient = QLinearGradient(0, 0, fill_width, 0)
                accent = QColor(theme.get('accent', '#007AFF'))
                accent_hover = QColor(theme.get('accent_hover', '#3395FF'))

                fill_gradient.setColorAt(0, accent)
                fill_gradient.setColorAt(0.5, accent_hover)
                fill_gradient.setColorAt(1, accent)

                # 圆角填充路径
                fill_path = QPainterPath()
                fill_path.addRoundedRect(fill_rect, radius, radius)
                painter.setBrush(fill_gradient)
                painter.drawPath(fill_path)

                # === 3. 流光效果 (shimmer) ===
                if self._shimmer_anim.state() == QPropertyAnimation.Running:
                    shimmer_x = self._shimmer_offset * (fill_width + 40) - 20
                    shimmer_gradient = QLinearGradient(shimmer_x, 0, shimmer_x + 20, 0)
                    shimmer_gradient.setColorAt(0, QColor(255, 255, 255, 0))
                    shimmer_gradient.setColorAt(0.5, QColor(255, 255, 255, 60))
                    shimmer_gradient.setColorAt(1, QColor(255, 255, 255, 0))

                    shimmer_rect = QRectF(fill_rect)
                    shimmer_rect.setWidth(fill_width)
                    shimmer_path = QPainterPath()
                    shimmer_path.addRoundedRect(shimmer_rect, radius, radius)
                    painter.setBrush(shimmer_gradient)
                    painter.setClipPath(shimmer_path)
                    painter.drawRect(shimmer_rect)
                    painter.setClipping(False)

                # === 4. 发光效果 (进度变化时) ===
                if self._glow_intensity > 0.01:
                    glow_color = QColor(accent)
                    glow_color.setAlpha(int(80 * self._glow_intensity))
                    painter.setBrush(glow_color)
                    painter.setPen(Qt.NoPen)
                    glow_rect = fill_rect.adjusted(-2, -1, 2, 1)
                    glow_path = QPainterPath()
                    glow_path.addRoundedRect(glow_rect, radius + 1, radius + 1)
                    painter.setOpacity(0.5 * self._glow_intensity)
                    painter.drawPath(glow_path)
                    painter.setOpacity(1.0)

        # === 5. 顶部高光 (玻璃质感) ===
        highlight_gradient = QLinearGradient(0, 0, 0, 2)
        highlight_gradient.setColorAt(0, QColor(255, 255, 255, 30))
        highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        highlight_rect = QRectF(rect.left() + 1, rect.top() + 1, rect.width() - 2, 2)
        painter.setBrush(highlight_gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(highlight_rect, 1, 1)
