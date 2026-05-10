# -*- coding: utf-8 -*-
"""
Encryption Studio 设计令牌。

Light 主题以 macOS Liquid Glass 为第一目标；非 macOS 平台使用同一套
语义 token 做 Qt/QSS 拟玻璃降级，避免为了兼容而牺牲 macOS 质感。
"""

THEMES = {
    "Light": {
        # macOS native vibrancy
        "macos_material": "NSVisualEffectMaterialUnderWindowBackground",
        "native_window_bg": "transparent",

        # Window / surfaces
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F8FBFF, stop:0.46 #EDF4FB, stop:1 #E6EEF8)",
        "bg_vibrancy": "rgba(245, 249, 255, 0.42)",
        "surface": "rgba(255, 255, 255, 0.30)",
        "sidebar": "rgba(255, 255, 255, 0.34)",
        "sidebar_hover": "rgba(255, 255, 255, 0.42)",
        "sidebar_active": "rgba(0, 122, 255, 0.14)",
        "sidebar_active_border": "rgba(0, 122, 255, 0.28)",
        "panel": "rgba(255, 255, 255, 0.46)",
        "panel_elevated": "rgba(255, 255, 255, 0.62)",
        "config_panel": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255,255,255,0.58), stop:1 rgba(255,255,255,0.34))",
        "config_panel_border": "rgba(255, 255, 255, 0.62)",
        "card_bg": "rgba(255, 255, 255, 0.34)",
        "card_bg_hover": "rgba(255, 255, 255, 0.48)",

        # Glass aliases used by custom painted widgets
        "glass_bg": "rgba(255, 255, 255, 0.42)",
        "glass_bg_strong": "rgba(255, 255, 255, 0.66)",
        "glass_border": "rgba(255, 255, 255, 0.64)",
        "glass_border_subtle": "rgba(255, 255, 255, 0.42)",
        "glass_shadow": "rgba(17, 24, 39, 0.08)",
        "inner_shadow": "rgba(17, 24, 39, 0.06)",

        # Apple blue
        "accent": "#007AFF",
        "accent_hover": "#2994FF",
        "accent_active": "#0067D8",
        "accent_light": "rgba(0, 122, 255, 0.12)",
        "accent_subtle": "rgba(0, 122, 255, 0.18)",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38A1FF, stop:1 #007AFF)",
        "accent_gradient_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5BB3FF, stop:1 #168BFF)",

        # State
        "success": "#34C759",
        "success_light": "rgba(52, 199, 89, 0.12)",
        "danger": "#FF3B30",
        "danger_hover": "#FF6961",
        "danger_light": "rgba(255, 59, 48, 0.12)",
        "warning": "#FF9F0A",

        # Text
        "fg": "#111827",
        "fg_secondary": "#4B5563",
        "fg_tertiary": "#8A94A6",
        "fg_muted": "#B7BFCC",

        # Lines
        "border": "rgba(255, 255, 255, 0.54)",
        "border_dark": "rgba(15, 23, 42, 0.08)",
        "border_focus": "rgba(0, 122, 255, 0.56)",
        "separator": "rgba(15, 23, 42, 0.08)",
        "highlight": "rgba(255, 255, 255, 0.78)",

        # Inputs
        "input_bg": "rgba(255, 255, 255, 0.54)",
        "input_bg_hover": "rgba(255, 255, 255, 0.68)",
        "input_border": "rgba(15, 23, 42, 0.08)",

        # Typography
        "sidebar_font_size": "13px",
        "sidebar_font_weight": "600",
        "section_title_size": "15px",
        "section_title_weight": "700",
        "section_title_letter": "0px",
        "body_size": "13px",
        "body_weight": "400",
        "caption_size": "11px",
        "caption_weight": "400",

        # Geometry
        "radius_xs": "6px",
        "radius_sm": "8px",
        "radius_md": "10px",
        "radius_lg": "16px",
        "radius_xl": "20px",

        # QSS cannot render box-shadow; these are semantic notes for custom painters.
        "shadow_sm": "rgba(15, 23, 42, 0.06)",
        "shadow_md": "rgba(15, 23, 42, 0.08)",
        "shadow_lg": "rgba(15, 23, 42, 0.10)",

        # Lists / drop zone
        "dropzone_bg": "rgba(255, 255, 255, 0.28)",
        "dropzone_border": "rgba(0, 122, 255, 0.24)",
        "dropzone_hover_bg": "rgba(0, 122, 255, 0.08)",
        "dropzone_hover_border": "rgba(0, 122, 255, 0.44)",
        "list_bg": "rgba(255, 255, 255, 0.30)",
        "list_item_hover": "rgba(255, 255, 255, 0.44)",
        "list_item_selected": "rgba(0, 122, 255, 0.16)",
    },

    "Dark": {
        "macos_material": "NSVisualEffectMaterialHUDWindow",
        "native_window_bg": "transparent",

        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B1020, stop:0.48 #111827, stop:1 #0B1020)",
        "bg_vibrancy": "rgba(10, 16, 32, 0.58)",
        "surface": "rgba(15, 23, 42, 0.42)",
        "sidebar": "rgba(15, 23, 42, 0.54)",
        "sidebar_hover": "rgba(255, 255, 255, 0.07)",
        "sidebar_active": "rgba(10, 132, 255, 0.18)",
        "sidebar_active_border": "rgba(10, 132, 255, 0.34)",
        "panel": "rgba(30, 41, 59, 0.54)",
        "panel_elevated": "rgba(51, 65, 85, 0.66)",
        "config_panel": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(30,41,59,0.72), stop:1 rgba(15,23,42,0.52))",
        "config_panel_border": "rgba(255, 255, 255, 0.10)",
        "card_bg": "rgba(15, 23, 42, 0.34)",
        "card_bg_hover": "rgba(30, 41, 59, 0.52)",

        "glass_bg": "rgba(30, 41, 59, 0.48)",
        "glass_bg_strong": "rgba(51, 65, 85, 0.68)",
        "glass_border": "rgba(255, 255, 255, 0.13)",
        "glass_border_subtle": "rgba(255, 255, 255, 0.08)",
        "glass_shadow": "rgba(0, 0, 0, 0.32)",
        "inner_shadow": "rgba(0, 0, 0, 0.22)",

        "accent": "#0A84FF",
        "accent_hover": "#3AA0FF",
        "accent_active": "#006EDB",
        "accent_light": "rgba(10, 132, 255, 0.16)",
        "accent_subtle": "rgba(10, 132, 255, 0.22)",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3AA0FF, stop:1 #0A84FF)",
        "accent_gradient_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #63B6FF, stop:1 #2B98FF)",

        "success": "#30D158",
        "success_light": "rgba(48, 209, 88, 0.15)",
        "danger": "#FF453A",
        "danger_hover": "#FF6961",
        "danger_light": "rgba(255, 69, 58, 0.14)",
        "warning": "#FFD60A",

        "fg": "#F8FAFC",
        "fg_secondary": "#CBD5E1",
        "fg_tertiary": "#94A3B8",
        "fg_muted": "#64748B",

        "border": "rgba(255, 255, 255, 0.11)",
        "border_dark": "rgba(0, 0, 0, 0.26)",
        "border_focus": "rgba(10, 132, 255, 0.62)",
        "separator": "rgba(255, 255, 255, 0.08)",
        "highlight": "rgba(255, 255, 255, 0.16)",

        "input_bg": "rgba(15, 23, 42, 0.48)",
        "input_bg_hover": "rgba(30, 41, 59, 0.62)",
        "input_border": "rgba(255, 255, 255, 0.10)",

        "sidebar_font_size": "13px",
        "sidebar_font_weight": "600",
        "section_title_size": "15px",
        "section_title_weight": "700",
        "section_title_letter": "0px",
        "body_size": "13px",
        "body_weight": "400",
        "caption_size": "11px",
        "caption_weight": "400",

        "radius_xs": "6px",
        "radius_sm": "8px",
        "radius_md": "10px",
        "radius_lg": "16px",
        "radius_xl": "20px",

        "shadow_sm": "rgba(0, 0, 0, 0.20)",
        "shadow_md": "rgba(0, 0, 0, 0.28)",
        "shadow_lg": "rgba(0, 0, 0, 0.36)",

        "dropzone_bg": "rgba(15, 23, 42, 0.30)",
        "dropzone_border": "rgba(10, 132, 255, 0.30)",
        "dropzone_hover_bg": "rgba(10, 132, 255, 0.12)",
        "dropzone_hover_border": "rgba(10, 132, 255, 0.52)",
        "list_bg": "rgba(15, 23, 42, 0.36)",
        "list_item_hover": "rgba(255, 255, 255, 0.06)",
        "list_item_selected": "rgba(10, 132, 255, 0.22)",
    },
}
