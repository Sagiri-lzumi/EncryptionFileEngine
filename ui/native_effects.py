# -*- coding: utf-8 -*-
"""
macOS 原生玻璃效果封装。

这个模块只负责 UI 材质增强：macOS 上尝试接入 NSVisualEffectView，
其他平台或依赖缺失时保持 Qt/QSS 拟玻璃效果。任何失败都必须降级，
不能影响主程序启动和加解密流程。
"""

import sys
import os
from ctypes import c_void_p

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

try:
    from core.logger import sys_logger
except Exception:  # pragma: no cover - 日志模块不可用时也不影响 UI 启动
    sys_logger = None


class NativeGlassController:
    """为主窗口提供可选的 macOS vibrancy 背景。"""

    def __init__(self, window):
        self.window = window
        self.is_active = False
        self.reason = ""
        self._effect_view = None
        self._logged_reason = False

    def apply(self, theme_data):
        """尝试启用原生玻璃；失败时返回 False 并使用 Qt 拟玻璃。"""
        if sys.platform != "darwin":
            self.reason = "native glass is only available on macOS"
            self.is_active = False
            return False
        if os.environ.get("ENCRYPTION_STUDIO_DISABLE_NATIVE_GLASS") == "1":
            self.reason = "native glass disabled by environment"
            self.is_active = False
            return False
        if QGuiApplication.platformName().lower() != "cocoa":
            self.reason = "Qt is not using the cocoa platform plugin"
            self.is_active = False
            return False
        if not self.window.isVisible():
            self.reason = "window is not visible yet"
            self.is_active = False
            return False

        try:
            self.window.setAttribute(Qt.WA_TranslucentBackground, True)
            self.window.setAutoFillBackground(False)

            import objc  # type: ignore
            from AppKit import (  # type: ignore
                NSVisualEffectView,
                NSVisualEffectStateActive,
                NSVisualEffectBlendingModeBehindWindow,
                NSViewHeightSizable,
                NSViewWidthSizable,
            )
            import AppKit  # type: ignore

            ns_view = objc.objc_object(c_void_p=int(self.window.winId()))
            ns_window = ns_view.window()
            if ns_window is None:
                self.reason = "NSWindow is not ready"
                self.is_active = False
                return False

            content_view = ns_window.contentView()
            if content_view is None:
                self.reason = "NSWindow contentView is not ready"
                self.is_active = False
                return False

            material = self._resolve_material(AppKit, theme_data)
            if self._effect_view is None:
                self._effect_view = NSVisualEffectView.alloc().initWithFrame_(content_view.bounds())
                self._effect_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
                self._effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
                self._effect_view.setState_(NSVisualEffectStateActive)
                below = getattr(AppKit, "NSWindowBelow", -1)
                content_view.addSubview_positioned_relativeTo_(self._effect_view, below, None)

            self._effect_view.setMaterial_(material)
            self._effect_view.setFrame_(content_view.bounds())
            self._effect_view.setHidden_(False)

            if hasattr(ns_window, "setOpaque_"):
                ns_window.setOpaque_(False)
            if hasattr(ns_window, "setBackgroundColor_") and hasattr(AppKit, "NSColor"):
                ns_window.setBackgroundColor_(AppKit.NSColor.clearColor())

            self.reason = ""
            self.is_active = True
            return True
        except Exception as exc:
            self.reason = str(exc)
            self.is_active = False
            if self._effect_view is not None:
                try:
                    self._effect_view.setHidden_(True)
                except Exception:
                    pass
            self._log_fallback_once()
            return False

    def _resolve_material(self, appkit, theme_data):
        """选择更接近浅色 Liquid Glass 的系统材质，兼容不同 macOS 版本。"""
        preferred = theme_data.get("macos_material", "NSVisualEffectMaterialUnderWindowBackground")
        fallback_names = (
            preferred,
            "NSVisualEffectMaterialUnderWindowBackground",
            "NSVisualEffectMaterialWindowBackground",
            "NSVisualEffectMaterialSidebar",
            "NSVisualEffectMaterialLight",
        )
        for name in fallback_names:
            if hasattr(appkit, name):
                return getattr(appkit, name)
        return 0

    def _log_fallback_once(self):
        if self._logged_reason or not self.reason:
            return
        self._logged_reason = True
        if sys_logger is not None:
            try:
                sys_logger.log(f"macOS 原生玻璃不可用，已使用 Qt 拟玻璃回退: {self.reason}")
            except Exception:
                pass
