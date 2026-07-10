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
    - ThemeToggleButton: 右上角日/月主题切换器（悬浮 overlay）

按钮组件:
    - ModernButton: Apple 风格主按钮，支持渐变和玻璃降级
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
    - GlassWidget: 液态玻璃效果 Widget

设计规范:
所有组件遵循 macOS Human Interface Guidelines，使用毛玻璃效果、
柔和阴影、高光边缘等视觉元素，保证跨平台一致性。
"""

from PySide6.QtWidgets import (QPushButton, QListWidget, QAbstractItemView, QCheckBox,
                                 QStyle, QStyleOptionButton, QWidget, QGraphicsBlurEffect,
                                 QScrollArea, QFrame, QVBoxLayout, QComboBox, QGraphicsDropShadowEffect,
                                 QGroupBox, QLabel, QLineEdit, QHBoxLayout, QStackedWidget)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRectF, Property, QRect, QPoint, QParallelAnimationGroup, Signal, QPointF, QSize
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen, QFont, QBrush, QLinearGradient, QFontMetrics, QGradient, QIcon
import os
import re

from ui.platform_fonts import get_system_font_family
from ui.icons import draw_icon, make_icon
from ui.themes import THEME_TOGGLE_SIZE, ICON_STROKE


def qcolor(value, fallback="#000000", alpha=None):
    """将主题 token 转成 QColor，兼容 QSS 的 rgba(...) 字符串。"""
    text = str(value or fallback).strip()
    match = re.fullmatch(r"rgba\(\s*(\d+),\s*(\d+),\s*(\d+),\s*([0-9.]+)\s*\)", text)
    if match:
        r, g, b = (int(match.group(i)) for i in range(1, 4))
        a_raw = float(match.group(4))
        color = QColor(r, g, b, int(255 * a_raw if a_raw <= 1 else a_raw))
    else:
        color = QColor(text)
        if not color.isValid():
            color = QColor(fallback)
    if alpha is not None:
        color.setAlpha(alpha)
    return color


class CleanStackedWidget(QStackedWidget):
    """Stacked widget that clears translucent backing pixels before each paint."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContentStack")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        native_glass = bool(getattr(getattr(self.window(), "native_glass", None), "is_active", False))
        clear_color = QColor(0, 0, 0, 0) if native_glass else qcolor(theme.get('bg_vibrancy', theme.get('panel')))
        painter.fillRect(self.rect(), clear_color)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        rect = QRectF(self.rect())
        radius = 16.0
        bg = qcolor(theme.get('bg_vibrancy', theme.get('panel', 'rgba(255,255,255,0.42)')))
        border = qcolor(theme.get('glass_border_subtle', 'rgba(255,255,255,0.24)'))

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        super().paintEvent(event)


class PageSurface(QFrame):
    """Stable page root used inside CleanStackedWidget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PageSurface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(False)


class IconBadge(QWidget):
    """Themed icon presenter for inline symbols and soft badges."""
    def __init__(self, icon_name="key", size=32, parent=None, accent=False, variant="badge"):
        super().__init__(parent)
        self.icon_name = icon_name
        self.variant = "accent_badge" if accent else variant
        self.setFixedSize(size, size)

    def set_icon(self, icon_name):
        self.icon_name = icon_name
        self.update()

    def set_variant(self, variant):
        self.variant = variant
        self.update()

    def paintEvent(self, event):
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        if self.variant == "inline":
            icon_color = qcolor(theme.get('fg_secondary', '#475569'))
            bg = None
            border = None
            icon_rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        elif self.variant == "accent_badge":
            icon_color = qcolor(theme.get('accent', '#007AFF'))
            bg = qcolor(theme.get('accent_light', 'rgba(0, 122, 255, 0.12)'))
            border = qcolor(theme.get('sidebar_active_border', 'rgba(0, 122, 255, 0.28)'))
            icon_rect = QRectF(self.rect()).adjusted(7, 7, -7, -7)
        else:
            icon_color = qcolor(theme.get('fg_secondary', '#475569'))
            bg = qcolor(theme.get('surface', 'rgba(248, 250, 252, 0.78)'))
            border = qcolor(theme.get('border', 'rgba(15, 23, 42, 0.08)'))
            bg.setAlpha(max(18, int(bg.alpha() * 0.72)))
            icon_rect = QRectF(self.rect()).adjusted(5, 5, -5, -5)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if bg is not None and border is not None:
            rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.setPen(QPen(border, 1.0))
            painter.setBrush(bg)
            painter.drawRoundedRect(rect, 8, 8)
        draw_icon(painter, self.icon_name, icon_rect, icon_color, ICON_STROKE)


class BrandLogoBadge(QWidget):
    """左上角品牌徽章：线形盾锁图标（无填色、纯线条），与侧栏导航按钮同款线风。

    渲染时从 ``self.window().theme_data`` 现取 accent 色，自动跟随主题切换
    （与 IconBadge 同机制），无需额外的 update_theme 接线。全矢量自绘、不
    依赖任何图片资源，跨平台一致。
    """
    def __init__(self, size=30, parent=None):
        super().__init__(parent)
        self.setObjectName("BrandLogoBadge")
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else None
        from ui.themes import THEMES
        theme = theme or THEMES["Light"]
        accent = qcolor(theme.get('accent', '#007AFF'))

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 内边距让线稿不贴边，与 IconBadge 视觉重量一致
        pad = 2.0
        icon_rect = QRectF(self.rect()).adjusted(pad, pad, -pad, -pad)
        draw_icon(painter, "brand-shield", icon_rect, accent, ICON_STROKE)


class SectionHeader(QWidget):
    """Compact icon + title row for cards and panels."""
    def __init__(self, title, icon_name="doc", parent=None):
        super().__init__(parent)
        self.setObjectName("SectionHeader")
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.badge = IconBadge(icon_name, 30, self, variant="badge")
        layout.addWidget(self.badge)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionHeaderTitle")
        self.title_label.setFont(QFont(get_system_font_family(), 12, QFont.DemiBold))
        layout.addWidget(self.title_label)
        layout.addStretch()

    def set_icon(self, icon_name):
        self.badge.set_icon(icon_name)


class TaskWorkspacePanel(QFrame):
    """Main task workspace: header, file queue body, and bottom tool row."""
    def __init__(self, title, subtitle, icon_name="folder", parent=None):
        super().__init__(parent)
        self.setObjectName("TaskWorkspacePanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        header = QWidget()
        header.setObjectName("WorkspaceHeader")
        h_header = QHBoxLayout(header)
        h_header.setContentsMargins(0, 0, 0, 0)
        h_header.setSpacing(12)

        self.badge = IconBadge(icon_name, 38, self, variant="badge")
        h_header.addWidget(self.badge)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("WorkspaceTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("WorkspaceSubtitle")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        h_header.addLayout(title_box)
        h_header.addStretch()
        # 避让右上角悬浮的 ThemeToggleButton overlay（size + 左右 margin + 投影间隙）:
        # 不改切换器定位，仅让计数药丸左移到其投影之外，两者互不遮挡。
        # 值同源 ui.themes.THEME_TOGGLE_AVOID，改切换器几何这里自动跟随，杜绝 50 魔数。
        from ui.themes import THEME_TOGGLE_AVOID
        h_header.addSpacing(THEME_TOGGLE_AVOID)

        self.count_label = QLabel("0 个文件")
        self.count_label.setObjectName("QueueCounter")
        h_header.addWidget(self.count_label)
        root.addWidget(header)

        self._content = QWidget()
        self._content.setObjectName("WorkspaceBody")
        # 启用样式背景，使 QSS 的 background:transparent 真正生效，
        # 避免非 macOS 关毛玻璃时被 Qt 用系统浅色填充冒白块。
        self._content.setAttribute(Qt.WA_StyledBackground, True)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        root.addWidget(self._content, 1)

        self._footer = QWidget()
        self._footer.setObjectName("WorkspaceToolbar")
        self._footer.setAttribute(Qt.WA_StyledBackground, True)
        self._footer_layout = QHBoxLayout(self._footer)
        self._footer_layout.setContentsMargins(0, 0, 0, 0)
        self._footer_layout.setSpacing(8)
        root.addWidget(self._footer)

    def content_layout(self):
        return self._content_layout

    def footer_layout(self):
        return self._footer_layout

    def set_count(self, count):
        self.count_label.setText(f"{count} 个文件")


class InspectorSection(QFrame):
    """Compact right-side inspector section with a stable header."""
    def __init__(self, title, icon_name="doc", parent=None):
        super().__init__(parent)
        self.setObjectName("InspectorSection")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)
        root.addWidget(SectionHeader(title, icon_name))

        self._content = QWidget()
        self._content.setObjectName("InspectorSectionContent")
        # 启用样式背景：InspectorSection 父框架是深色 surface，子内容用 transparent
        # 需 WA_StyledBackground 才能让 QSS background 生效，避免冒系统浅色。
        self._content.setAttribute(Qt.WA_StyledBackground, True)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)
        root.addWidget(self._content)

    def content_layout(self):
        return self._content_layout


class KeyPairListRow(QFrame):
    """Compact visual row for one RSA key pair in the key manager."""
    def __init__(self, key_name, public_file=None, private_file=None, parent=None):
        super().__init__(parent)
        self.setObjectName("KeyPairListRow")
        self.setMinimumHeight(60)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(10)

        root.addWidget(IconBadge("keypair", 34, self, accent=True))

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(2)

        self.title_label = QLabel(key_name)
        self.title_label.setObjectName("KeyPairName")
        self.title_label.setToolTip(key_name)
        text_box.addWidget(self.title_label)

        public_text = public_file or "缺少公钥"
        private_text = private_file or "缺少私钥"
        self.meta_label = QLabel(f"公钥 {public_text}   ·   私钥 {private_text}")
        self.meta_label.setObjectName("KeyPairMeta")
        self.meta_label.setToolTip(f"公钥: {public_text}\n私钥: {private_text}")
        text_box.addWidget(self.meta_label)

        root.addLayout(text_box, 1)

        ready = bool(public_file and private_file)
        self.status_label = QLabel("完整" if ready else "缺失")
        self.status_label.setObjectName("KeyPairStatus")
        self.status_label.setProperty("state", "ready" if ready else "warning")
        root.addWidget(self.status_label)


class ExecutionFooter(QFrame):
    """Bottom execution area combining status, progress, and action stack."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExecutionFooter")
        self.setFixedHeight(118)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 14)
        root.setSpacing(9)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)

        title = QLabel("执行状态")
        title.setObjectName("ExecutionTitle")
        status_row.addWidget(title)
        status_row.addStretch()

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("StatusLabel")
        status_row.addWidget(self.status_label)
        root.addLayout(status_row)

        self.progress_bar = GlassProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.actions_stack = QStackedWidget()
        self.actions_stack.setObjectName("ExecutionActions")
        self.actions_stack.setFixedHeight(50)
        root.addWidget(self.actions_stack)


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
        arrow_color = qcolor(theme.get('fg_secondary', '#64748B'))

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
        # 用前景色亮度判定深色主题：亮色文字 => 深色背景 => is_dark。
        # 旧实现写死 == '#F8FAFC'，但 Dark 主题的 fg 是 #F4F7FB，永远不匹配，
        # 导致 Dark 模式滚动条手柄误用浅色模式的深色，在深底上几乎不可见。
        fg = qcolor(theme_data.get('fg', '#111827'))
        is_dark = fg.lightness() > 128
        handle_bg = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(15, 23, 42, 0.16)"
        handle_hover = "rgba(255, 255, 255, 0.34)" if is_dark else "rgba(15, 23, 42, 0.24)"
        handle_pressed = "rgba(255, 255, 255, 0.44)" if is_dark else "rgba(15, 23, 42, 0.32)"
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
                background: {handle_bg};
                min-height: 30px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {handle_pressed};
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
        self._content.setAttribute(Qt.WA_StyledBackground, True)
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

        # 主题缓存：避免 paintEvent 每帧 from import + self.window().theme_data 链查。
        # 由 MainWindow.apply_theme 喂入；未喂入时在 paintEvent 首帧惰性取一次兜底。
        self._theme = None

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

    def update_theme(self, theme):
        """缓存主题，供 paintEvent 直接读取，避免每帧 import/链查。"""
        self._theme = theme
        self.update()

    def _sync_progress_to_state(self, animate):
        """
        把 _check_progress 对齐到当前 isChecked()。

        - animate=True（用户鼠标点击走 nextCheckState）：跑 180ms 过渡，有勾出动画。
        - animate=False（setChecked 等程序化置位）：直接对齐进度、不跑动画，
          避免程序化改变又触发一段动画/连锁，消除“选中态变了进度没变”的错乱（R2）。
        无论哪条路径都显式 setStartValue，避免快速连点时动画从上次的中间值
        或旧 startValue 起而出现“勾回退/愣一下”的间歇卡顿（R1）。
        """
        target = 1.0 if self.isChecked() else 0.0
        self._check_anim.stop()
        if animate:
            self._check_anim.setStartValue(self._check_progress)
            self._check_anim.setEndValue(target)
            self._check_anim.start()
        else:
            self._check_progress = target
            self.update()

    def setChecked(self, checked):
        """
        程序化置位：同步进度但不跑动画。
        覆写后 check_constraints 里大量的 setChecked(False) 不再留下
        “选中态已变为 unchecked、_check_progress 仍停在 1.0”的脱钩隐患。
        """
        super().setChecked(checked)
        self._sync_progress_to_state(animate=False)

    def nextCheckState(self):
        """用户鼠标点击切换选中状态时触发动画"""
        super().nextCheckState()
        self._sync_progress_to_state(animate=True)

    def paintEvent(self, event):
        """自定义绘制复选框和文字"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 主题优先用缓存；未喂入则惰性取一次（常态下 apply_theme 已喂入，此兜底极少走到）。
        theme = self._theme
        if theme is None:
            from ui.themes import THEMES
            theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]
        enabled = self.isEnabled()

        # 复选框尺寸和位置
        box_size = 20
        box_x = 2
        box_y = (self.height() - box_size) // 2
        box_rect = QRect(box_x, box_y, box_size, box_size)

        # 绘制背景 - 毛玻璃效果；禁用态必须明确，避免用户误以为选项可点击。
        if self._check_progress > 0:
            accent = qcolor(theme['accent'])
            if enabled:
                gradient = QLinearGradient(box_rect.topLeft(), box_rect.bottomLeft())
                gradient.setColorAt(0, accent.lighter(110))
                gradient.setColorAt(1, accent)
                painter.setBrush(gradient)
                painter.setPen(Qt.NoPen)
            else:
                accent.setAlpha(70)
                painter.setBrush(accent)
                painter.setPen(QPen(qcolor(theme.get('input_border', '#CBD5E1'), alpha=90), 1.2))
        else:
            bg_color = qcolor(theme.get('input_bg', 'rgba(255, 255, 255, 0.86)'))
            border_color = qcolor(theme.get('input_border', 'rgba(15, 23, 42, 0.10)'))
            if not enabled:
                bg_color = qcolor(theme.get('surface', 'rgba(248, 250, 252, 0.78)'))
                bg_color.setAlpha(max(24, int(bg_color.alpha() * 0.55)))
                border_color = qcolor(theme.get('border', 'rgba(15, 23, 42, 0.08)'))
                border_color.setAlpha(max(24, int(border_color.alpha() * 0.55)))
            painter.setBrush(bg_color)
            painter.setPen(QPen(border_color, 1.2))

        painter.drawRoundedRect(box_rect, 6, 6)

        # 绘制对钩（带动画）
        if self._check_progress > 0.01:
            check_color = QColor("white") if enabled else qcolor(theme.get('fg_tertiary', '#94A3B8'))
            painter.setPen(QPen(check_color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
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
            painter.setPen(qcolor(theme['fg'] if enabled else theme.get('fg_tertiary', '#94A3B8')))
            font = self.font()
            font.setPointSize(12)
            font.setWeight(QFont.Medium)
            painter.setFont(font)
            text_rect = QRect(box_x + box_size + 12, 0, self.width() - box_x - box_size - 12, self.height())
            # 省略文字恒定，仅随 (text, 可用宽度) 变化，缓存后避免每帧重建 QFontMetrics + 重算 elidedText。
            avail_w = max(0, text_rect.width())
            cache_key = (self.text(), avail_w)
            if getattr(self, "_elided_cache_key", None) != cache_key:
                self._elided_cache_key = cache_key
                self._elided_cache_text = QFontMetrics(font).elidedText(self.text(), Qt.ElideRight, avail_w)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._elided_cache_text)


class AnimatedSidebarButton(QPushButton):
    """
    Apple 风格侧边栏导航按钮 - 毛玻璃胶囊选中态

    用于侧边栏导航，提供以下特性：
        - 由主窗口显式控制选中态，避免 Qt autoExclusive 触发重复动画
        - 悬停动画：鼠标悬停时背景渐变
        - 选中动画：选中时显示蓝色半透明胶囊背景
        - 顶部高光：模拟玻璃厚度的顶部高光线条
        - 轻量字标 + 文字组合显示

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
            icon_emoji: 轻量图标标识，如 "lock" / "key"
            parent: 父组件
        """
        super().__init__(text, parent)
        self.setCheckable(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.icon_emoji = icon_emoji
        self.setFont(QFont(get_system_font_family(), 11, QFont.DemiBold))

        # 动画属性
        self._hover_progress = 0.0
        self._check_progress = 0.0
        self._selected = False

        # 悬停动画
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(200)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 选中动画
        self._check_anim = QPropertyAnimation(self, b"checkProgress", self)
        self._check_anim.setDuration(250)
        self._check_anim.setEasingCurve(QEasingCurve.OutCubic)

    def set_selected(self, selected: bool, animate: bool = True):
        """Set navigation selection explicitly without Qt auto-exclusive jitter."""
        if self._selected == selected and abs(self._check_progress - (1.0 if selected else 0.0)) < 0.001:
            return
        self._selected = selected
        target = 1.0 if selected else 0.0
        self._check_anim.stop()
        if animate:
            self._check_anim.setStartValue(self._check_progress)
            self._check_anim.setEndValue(target)
            self._check_anim.start()
        else:
            self._check_progress = target
            self.update()

    def is_selected(self):
        return self._selected

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]

        # 每帧先清底，清除上一帧残留的半透明 hover/选中像素。否则默认
        # CompositionMode_SourceOver 会把新一帧半透明背景叠在旧帧之上，鼠标快速
        # 来回时半透明层层累加 → 底色越来越深呈深灰 → “抽搐”。
        # 清底色用“侧栏 sidebar 色”而非透明：透明会擦穿父侧栏半透明色、露出
        # 窗口 bg 渐变实色，使 hover 之外变成“与环境色不同的长方形、圆角感丢失”。
        # 清成 sidebar 色既擦掉残留，又让按钮区维持侧栏正常观感、保留 capsule
        # 圆角 hover 的对比。Source 模式按源 alpha 覆盖，故把 alpha 拉满不透明。
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        side_bg = qcolor(theme.get('sidebar', 'rgba(248,250,252,0.84)'))
        side_bg.setAlpha(255)
        painter.fillRect(self.rect(), side_bg)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        rect = self.rect()

        # === 胶囊背景区域 ===
        capsule_rect = rect.adjusted(6, 4, -6, -4)
        radius = 8

        if self._hover_progress > 0.01 and self._check_progress < 0.01:
            hover_bg = qcolor(theme.get('sidebar_hover', 'rgba(255, 255, 255, 0.45)'))
            hover_bg.setAlpha(max(18, int(120 * self._hover_progress)))
            painter.setBrush(hover_bg)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(capsule_rect, radius, radius)

        if self._check_progress > 0.01:
            accent_hex = theme.get('accent', '#6366F1')
            accent_color = qcolor(accent_hex)
            active_bg = qcolor(theme.get('sidebar_active', 'rgba(0, 122, 255, 0.14)'))
            active_bg.setAlpha(int(active_bg.alpha() * self._check_progress))
            painter.setBrush(active_bg)
            painter.setPen(QPen(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(78 * self._check_progress)), 1.0))
            painter.drawRoundedRect(capsule_rect, radius, radius)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(accent_color.red(), accent_color.green(), accent_color.blue(), int(150 * self._check_progress)))
            painter.drawRoundedRect(QRectF(capsule_rect.left() + 1.5, capsule_rect.top() + 8, 2, capsule_rect.height() - 16), 1, 1)

        accent_color = qcolor(theme.get('accent', '#007AFF'))
        icon_color = accent_color if self._check_progress > 0.35 else qcolor(theme.get('fg_tertiary', '#94A3B8'))
        # 以 44×210 校准，与旧硬坐标 (21,12,20×20) 逐像素等价；改相对计算后
        # 行高/宽度/字号一变也不会错位。round 防止 Retina(DPR=2)亚像素糊。
        icon_size = 20
        ix = round(rect.left() + 21)
        iy = rect.center().y() - icon_size / 2      # 44 高下 = 12 ✓
        icon_rect = QRectF(ix, iy, icon_size, icon_size)
        draw_icon(painter, self.icon_emoji, icon_rect, icon_color, ICON_STROKE)

        if self._check_progress > 0.35:
            accent_hex = theme.get('accent', '#6366F1')
            text_color = qcolor(accent_hex)
        else:
            text_color = qcolor(theme.get('fg', '#1D1D1F'))
        painter.setPen(text_color)
        font_text = self.font()
        font_text.setPointSize(11)
        font_text.setWeight(QFont.DemiBold)
        painter.setFont(font_text)
        # 文字紧跟图标右缘 + 原间隙 13 → tx = 54 ✓；可用宽随右缘走 = width-62 ✓
        tx = ix + icon_size + 13
        tw = rect.right() - tx - 8
        painter.drawText(QRectF(tx, 0, tw, rect.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class SidebarNavButton(AnimatedSidebarButton):
    """Compatibility alias with the explicit stable navigation API."""
    pass


class ThemeToggleButton(QPushButton):
    """右上角主题切换按钮：太阳/月亮，点击临时切换主题。

    根据当前应用的主题（``self.window().theme_data`` 的 fg 亮度）画日（Light）
    或月（Dark），paint 时现取主题 → 自动跟随。颜色用 ``fg_secondary``、hover
    微淡圆形底。语义：始终跟随系统，点击仅临时预览（不持久，由主窗口在
    colorSchemeChanged 信号到来时纠正回系统主题）。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeToggleButton")
        self.setFixedSize(THEME_TOGGLE_SIZE, THEME_TOGGLE_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        # 自绘 paintEvent 已清底透明；该属性让 Qt 知道控件自身透明，跨平台兜底，
        # 防部分平台插件在 paintEvent 之外仍绘 QPushButton native 非透明方形底。
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._hover_progress = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, v):
        self._hover_progress = float(v)
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        from ui.themes import THEMES
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Light"]
        # 用 fg 亮度判定当前主题深浅（与 SmoothScrollArea 同口径）
        fg = qcolor(theme.get('fg', '#111827'))
        is_dark = fg.lightness() > 128

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        # 清底：透明，切回器自身背景透明透出顶栏/窗口
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        rect = QRectF(self.rect())
        # hover 淡圆形底
        if self._hover_progress > 0.01:
            hover_bg = qcolor(theme.get('sidebar_hover', 'rgba(15,23,42,0.045)'))
            hover_bg.setAlpha(max(18, int(110 * self._hover_progress)))
            painter.setPen(Qt.NoPen)
            painter.setBrush(hover_bg)
            # 胶囊 hover 底：与 AnimatedSidebarButton 同款圆角矩形(radius=7，
            # 34 高下接近正圆胶囊带切角语义)；旧版 drawEllipse 是 30px 圆、比 22px
            # 图标大像散光圈，现与侧栏按钮 hover 形态统一。
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 7, 7)

        icon_color = qcolor(theme.get('fg_secondary', '#475569'))
        # 复用 ui/icons.py 的矢量 sun/moon：与侧栏/徽标同款线风，弯月左右对称、
        # 与太阳同坐标系视觉重量一致，告别自绘 OddEvenFill 实心月牙"被啃一块"的观感。
        icon_name = "moon" if is_dark else "sun"
        icon_rect = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        draw_icon(painter, icon_name, icon_rect, icon_color, ICON_STROKE)


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

    def __init__(self, text="", color_type="normal", icon_name=None, parent=None):
        """
        初始化按钮

        参数:
            text: 按钮显示文本
            color_type: 按钮类型 ("primary", "danger", "normal")
            icon_name: 可选的内置矢量图标名称
            parent: 父组件
        """
        if parent is None and isinstance(icon_name, QWidget):
            parent = icon_name
            icon_name = None
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.color_type = color_type
        self.icon_name = icon_name
        self._last_icon_color = None
        self.setFont(QFont(get_system_font_family(), 11, QFont.DemiBold))
        self.setIconSize(QSize(18, 18))
        if icon_name:
            # 下限放低，让按钮按内容(图标+文字)自适应，而不是被 92 卡住
            # 把最末字顶到右 padding 之外被裁。
            self.setMinimumWidth(76)

        # 点击动画属性
        self._press_scale = 1.0
        self._press_anim = QPropertyAnimation(self, b"pressScale", self)
        self._press_anim.setDuration(100)
        self._press_anim.setEasingCurve(QEasingCurve.OutQuad)

    def set_icon_name(self, icon_name):
        self.icon_name = icon_name
        self._last_icon_color = None
        if icon_name:
            theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else None
            if theme:
                self.update_theme(theme)
        else:
            self.setIcon(QIcon())

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
        if self.icon_name:
            if self.color_type == "primary":
                icon_color = "#ffffff"
            elif self.color_type == "danger":
                icon_color = theme.get('danger', '#FF3B30')
            else:
                icon_color = theme.get('fg_secondary', '#4B5563')
            if icon_color != self._last_icon_color:
                self.setIcon(make_icon(self.icon_name, icon_color, 18, ICON_STROKE))
                self._last_icon_color = icon_color

        if self.color_type == "primary":
            style = f"""
                QPushButton {{
                    background: {theme.get('accent_gradient', '#007AFF')};
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.42);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.14);
                    border-radius: 10px;
                    padding: 0 24px;
                    font-weight: 700;
                    font-size: 14px;
                    min-height: {theme.get('control_primary_height', '48px')};
                }}
                QPushButton:hover {{
                    background: {theme.get('accent_gradient_hover', '#2994FF')};
                }}
                QPushButton:pressed {{
                    background: {theme.get('accent_active', '#0067D8')};
                }}
                QPushButton:disabled {{
                    background: {theme.get('card_bg', 'rgba(255, 255, 255, 0.34)')};
                    color: {theme.get('fg_tertiary', '#8A94A6')};
                }}
            """
        elif self.color_type == "danger":
            style = f"""
                QPushButton {{
                    background: {theme.get('danger_light', 'rgba(255, 59, 48, 0.12)')};
                    color: {theme.get('danger', '#FF3B30')};
                    border: 1px solid rgba(255, 59, 48, 0.24);
                    border-bottom: 1px solid rgba(255, 59, 48, 0.30);
                    border-radius: 10px;
                    padding: 0 22px;
                    font-weight: 600;
                    font-size: 14px;
                    min-height: {theme.get('control_primary_height', '48px')};
                }}
                QPushButton:hover {{
                    background: rgba(255, 59, 48, 0.18);
                    color: {theme.get('danger_hover', '#FF6961')};
                }}
                QPushButton:pressed {{
                    background: rgba(255, 59, 48, 0.24);
                }}
                QPushButton:disabled {{
                    background: {theme.get('card_bg', 'rgba(255, 255, 255, 0.34)')};
                    color: {theme.get('fg_tertiary', '#8A94A6')};
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background: {theme.get('card_bg', 'rgba(255, 255, 255, 0.34)')};
                    color: {theme.get('fg', '#1D1D1F')};
                    border: 1px solid {theme.get('glass_border_subtle', 'rgba(255, 255, 255, 0.42)')};
                    border-bottom: 1px solid {theme.get('border_dark', 'rgba(15, 23, 42, 0.08)')};
                    border-radius: 9px;
                    padding: 0 14px 0 16px;
                    font-weight: 600;
                    font-size: 13px;
                    min-height: {theme.get('control_height', '40px')};
                }}
                QPushButton:hover {{
                    background: {theme.get('card_bg_hover', 'rgba(255, 255, 255, 0.48)')};
                    border: 1px solid {theme.get('glass_border', 'rgba(255, 255, 255, 0.64)')};
                }}
                QPushButton:pressed {{
                    background: {theme.get('panel', 'rgba(255, 255, 255, 0.46)')};
                }}
                QPushButton:disabled {{
                    background: {theme.get('surface', 'rgba(255, 255, 255, 0.30)')};
                    color: {theme.get('fg_tertiary', '#8A94A6')};
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
    queue_changed = Signal()

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
                self.queue_changed.emit()
                if hasattr(self.window(), 'check_constraints'):
                    self.window().check_constraints()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.viewport().rect().adjusted(20, 20, -20, -20)

            if self._drag_hover:
                bg = qcolor(self.theme_data.get('dropzone_hover_bg', 'rgba(0, 122, 255, 0.08)'))
                pen = QPen(qcolor(self.theme_data.get('dropzone_hover_border', 'rgba(0, 122, 255, 0.44)')))
            else:
                bg = qcolor(self.theme_data.get('dropzone_bg', 'rgba(255, 255, 255, 0.28)'))
                pen = QPen(qcolor(self.theme_data.get('dropzone_border', 'rgba(0, 122, 255, 0.24)')))

            painter.setBrush(bg)
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1.5)
            pen.setDashPattern([6, 4])
            painter.setPen(pen)
            painter.drawRoundedRect(rect, 12, 12)

            # 提示文字 - 更精致的排版
            painter.setPen(qcolor(self.theme_data.get('fg_secondary', 'rgba(0, 0, 0, 0.50)')))
            font = QFont(get_system_font_family(), 13)
            font.setWeight(QFont.Medium)
            painter.setFont(font)

            # 图标 + 文字
            icon_rect = QRectF(rect.center().x() - 22, rect.center().y() - 46, 44, 44)
            icon_bg = qcolor(self.theme_data.get('accent_light', 'rgba(0, 122, 255, 0.12)'))
            icon_border = qcolor(self.theme_data.get('sidebar_active_border', 'rgba(0, 122, 255, 0.28)'))
            painter.setBrush(icon_bg)
            painter.setPen(QPen(icon_border, 1.0))
            painter.drawRoundedRect(icon_rect, 12, 12)
            draw_icon(
                painter,
                "folder-plus",
                icon_rect.adjusted(10, 10, -10, -10),
                qcolor(self.theme_data.get('accent', '#007AFF')),
                ICON_STROKE,
            )

            # 主文字
            painter.setPen(qcolor(self.theme_data.get('fg_secondary', 'rgba(0, 0, 0, 0.50)')))
            font_text = QFont(get_system_font_family(), 13)
            font_text.setWeight(QFont.Medium)
            painter.setFont(font_text)
            text_rect = QRectF(rect.left(), rect.center().y() + 8, rect.width(), 30)
            painter.drawText(text_rect, Qt.AlignCenter, "拖拽文件或文件夹到此处")

            # 副文字
            font_sub = QFont(get_system_font_family(), 11)
            font_sub.setWeight(QFont.Normal)
            painter.setFont(font_sub)
            painter.setPen(qcolor(self.theme_data.get('fg_tertiary', 'rgba(0, 0, 0, 0.35)')))
            sub_rect = QRectF(rect.left(), rect.center().y() + 32, rect.width(), 25)
            painter.drawText(sub_rect, Qt.AlignCenter, "支持批量添加，也可以使用下方按钮")


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
        painter.setBrush(qcolor(theme.get('glass_shadow', 'rgba(17, 24, 39, 0.08)')))
        painter.drawPath(shadow_path)

        # 2. 绘制渐变背景
        # background: linear-gradient(135deg, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0.4) 100%)
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, qcolor(theme.get('glass_bg_strong', 'rgba(255, 255, 255, 0.66)')))
        gradient.setColorAt(1, qcolor(theme.get('glass_bg', 'rgba(255, 255, 255, 0.42)')))

        bg_path = QPainterPath()
        bg_path.addRoundedRect(rect, radius, radius)
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPath(bg_path)

        # 3. 绘制高光边缘 (1px 描边模拟玻璃切面)
        # border: 1px solid rgba(255, 255, 255, 0.6)
        painter.setPen(QPen(qcolor(theme.get('glass_border', 'rgba(255, 255, 255, 0.64)')), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # 4. 底部边缘 (光线自上而下的衰减)
        # border-bottom: 1px solid rgba(255, 255, 255, 0.3)
        bottom_line = QPainterPath()
        bottom_y = rect.bottom() - 1
        bottom_line.moveTo(rect.left() + radius, bottom_y)
        bottom_line.lineTo(rect.right() - radius, bottom_y)
        painter.setPen(QPen(qcolor(theme.get('glass_border_subtle', 'rgba(255, 255, 255, 0.42)')), 1.0))
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
        self._content.setAttribute(Qt.WA_StyledBackground, True)
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

        painter.setPen(Qt.NoPen)
        painter.setBrush(qcolor(theme.get('card_bg', 'rgba(255, 255, 255, 0.34)')))
        painter.drawRoundedRect(rect, radius, radius)

        painter.setPen(QPen(qcolor(theme.get('glass_border_subtle', 'rgba(255, 255, 255, 0.42)')), 1.0))
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
        # 统一跟随主题 token，避免系统切换按钮脱离整体视觉体系。
        progress = self._switch_progress

        old_start = qcolor(theme.get('accent_hover', '#2994FF'))
        old_end = qcolor(theme.get('accent', '#007AFF'))
        new_start = qcolor(theme.get('success', '#34C759')).lighter(112)
        new_end = qcolor(theme.get('success', '#34C759'))

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
                accent = qcolor(theme.get('accent', '#007AFF'))
                accent_hover = qcolor(theme.get('accent_hover', '#3395FF'))

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
