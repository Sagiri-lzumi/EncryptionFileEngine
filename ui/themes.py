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
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F3F6FA, stop:0.52 #EEF2F7, stop:1 #E8EEF6)",
        "bg_vibrancy": "rgba(241, 245, 249, 0.86)",
        "surface": "rgba(248, 250, 252, 0.78)",
        "sidebar": "rgba(248, 250, 252, 0.84)",
        "sidebar_hover": "rgba(15, 23, 42, 0.045)",
        "sidebar_active": "rgba(0, 122, 255, 0.10)",
        "sidebar_active_border": "rgba(0, 122, 255, 0.24)",
        "panel": "rgba(255, 255, 255, 0.74)",
        "panel_elevated": "rgba(255, 255, 255, 0.90)",
        "config_panel": "rgba(248, 250, 252, 0.82)",
        "config_panel_border": "rgba(15, 23, 42, 0.075)",
        "card_bg": "rgba(255, 255, 255, 0.78)",
        "card_bg_hover": "rgba(255, 255, 255, 0.94)",

        # Glass aliases used by custom painted widgets
        "glass_bg": "rgba(255, 255, 255, 0.68)",
        "glass_bg_strong": "rgba(255, 255, 255, 0.88)",
        "glass_border": "rgba(15, 23, 42, 0.085)",
        "glass_border_subtle": "rgba(15, 23, 42, 0.06)",
        "glass_shadow": "rgba(15, 23, 42, 0.045)",
        "inner_shadow": "rgba(15, 23, 42, 0.045)",

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
        "fg_secondary": "#475569",
        "fg_tertiary": "#94A3B8",
        "fg_muted": "#CBD5E1",

        # Lines
        "border": "rgba(15, 23, 42, 0.08)",
        "border_dark": "rgba(15, 23, 42, 0.10)",
        "border_focus": "rgba(0, 122, 255, 0.56)",
        "separator": "rgba(15, 23, 42, 0.08)",
        "highlight": "rgba(15, 23, 42, 0.05)",

        # Inputs
        "input_bg": "rgba(255, 255, 255, 0.86)",
        "input_bg_hover": "rgba(255, 255, 255, 0.96)",
        "input_border": "rgba(15, 23, 42, 0.10)",

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
        "list_bg": "rgba(248, 250, 252, 0.74)",
        "list_item_hover": "rgba(15, 23, 42, 0.045)",
        "list_item_selected": "rgba(0, 122, 255, 0.12)",
    },

    "Dark": {
        "macos_material": "NSVisualEffectMaterialHUDWindow",
        "native_window_bg": "transparent",

        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #12161D, stop:0.52 #171C24, stop:1 #10141B)",
        "bg_vibrancy": "rgba(18, 22, 29, 0.92)",
        "surface": "rgba(31, 37, 48, 0.78)",
        "sidebar": "rgba(26, 31, 40, 0.92)",
        "sidebar_hover": "rgba(255, 255, 255, 0.055)",
        "sidebar_active": "rgba(10, 132, 255, 0.16)",
        "sidebar_active_border": "rgba(10, 132, 255, 0.30)",
        "panel": "rgba(28, 34, 44, 0.90)",
        "panel_elevated": "rgba(35, 42, 54, 0.94)",
        "config_panel": "rgba(24, 29, 38, 0.94)",
        "config_panel_border": "rgba(255, 255, 255, 0.12)",
        "card_bg": "rgba(32, 38, 49, 0.92)",
        "card_bg_hover": "rgba(42, 50, 64, 0.96)",

        "glass_bg": "rgba(32, 38, 49, 0.88)",
        "glass_bg_strong": "rgba(42, 50, 64, 0.94)",
        "glass_border": "rgba(255, 255, 255, 0.14)",
        "glass_border_subtle": "rgba(255, 255, 255, 0.10)",
        "glass_shadow": "rgba(0, 0, 0, 0.34)",
        "inner_shadow": "rgba(0, 0, 0, 0.24)",

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

        "fg": "#F4F7FB",
        "fg_secondary": "#C5CEDA",
        "fg_tertiary": "#8793A3",
        "fg_muted": "#566273",

        "border": "rgba(255, 255, 255, 0.13)",
        "border_dark": "rgba(0, 0, 0, 0.34)",
        "border_focus": "rgba(10, 132, 255, 0.62)",
        "separator": "rgba(255, 255, 255, 0.11)",
        "highlight": "rgba(255, 255, 255, 0.10)",

        "input_bg": "rgba(18, 23, 31, 0.92)",
        "input_bg_hover": "rgba(24, 30, 40, 0.98)",
        "input_border": "rgba(255, 255, 255, 0.13)",

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

        "dropzone_bg": "rgba(20, 25, 33, 0.70)",
        "dropzone_border": "rgba(10, 132, 255, 0.30)",
        "dropzone_hover_bg": "rgba(10, 132, 255, 0.12)",
        "dropzone_hover_border": "rgba(10, 132, 255, 0.52)",
        "list_bg": "rgba(18, 23, 31, 0.78)",
        "list_item_hover": "rgba(255, 255, 255, 0.055)",
        "list_item_selected": "rgba(10, 132, 255, 0.18)",
    },
}
