THEMES = {
    "Light": {
        # ============================================
        # 清新优雅主题 - 类 Notion/Linear 风格
        # ============================================

        # === 全局背景 ===
        # 柔和的灰白色渐变，比 macOS 默认更温暖
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F8F9FA, stop:0.5 #F1F3F5, stop:1 #EBEEF2)",
        "bg_vibrancy": "rgba(248, 249, 250, 0.95)",

        # === 毛玻璃面板 ===
        "glass_bg": "rgba(255, 255, 255, 0.82)",
        "glass_gradient_start": "rgba(255, 255, 255, 0.88)",
        "glass_gradient_end": "rgba(248, 248, 250, 0.75)",
        "glass_bg_hover": "rgba(255, 255, 255, 0.92)",
        "glass_bg_strong": "rgba(255, 255, 255, 0.95)",

        # === 边框与高光 ===
        "glass_border": "rgba(0, 0, 0, 0.08)",  # 更柔和的边框
        "glass_border_bottom": "rgba(0, 0, 0, 0.05)",
        "glass_border_subtle": "rgba(0, 0, 0, 0.05)",
        "glass_border_dark": "rgba(0, 0, 0, 0.06)",

        # === 阴影系统 ===
        "shadow_sm": "0 1px 3px rgba(0, 0, 0, 0.04)",
        "shadow_glass": "0 4px 16px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
        "shadow_md": "0 2px 8px rgba(0, 0, 0, 0.05)",
        "shadow_lg": "0 4px 24px rgba(0, 0, 0, 0.07)",
        "shadow_xl": "0 8px 32px rgba(0, 0, 0, 0.08)",
        "shadow_glow": "0 2px 8px rgba(99, 102, 241, 0.15)",  # 使用紫蓝色
        "shadow_primary_btn": "0 2px 4px rgba(99, 102, 241, 0.25)",

        # === 侧边栏 ===
        "sidebar": "rgba(249, 250, 251, 0.90)",
        "sidebar_hover": "rgba(0, 0, 0, 0.04)",
        "sidebar_active": "rgba(99, 102, 241, 0.12)",  # 紫蓝色选中
        "sidebar_active_border": "rgba(99, 102, 241, 0.25)",
        "sidebar_pill_radius": "8px",

        # === 内容面板 ===
        "panel": "rgba(255, 255, 255, 0.70)",
        "panel_elevated": "rgba(255, 255, 255, 0.85)",
        "panel_border": "rgba(0, 0, 0, 0.06)",

        # === 拖拽区域 ===
        "dropzone_bg": "rgba(248, 250, 251, 0.60)",
        "dropzone_border": "rgba(99, 102, 241, 0.20)",
        "dropzone_border_dash": "rgba(0, 0, 0, 0.10)",
        "dropzone_hover_bg": "rgba(99, 102, 241, 0.06)",

        # === 输入控件 ===
        "input_bg": "rgba(249, 250, 251, 0.80)",
        "input_bg_focus": "rgba(255, 255, 255, 0.95)",
        "input_border": "rgba(0, 0, 0, 0.08)",
        "input_border_focus": "rgba(99, 102, 241, 0.40)",
        "input_shadow_inset": "inset 0 1px 2px rgba(0, 0, 0, 0.03)",
        "input_radius": "8px",

        # === 色彩系统 ===
        "fg": "#1F2937",
        "fg_secondary": "rgba(31, 41, 55, 0.60)",
        "fg_tertiary": "rgba(31, 41, 55, 0.40)",
        "fg_muted": "rgba(31, 41, 55, 0.30)",

        # 主色调：紫蓝色 (Indigo) 比蓝色更优雅
        "accent": "#6366F1",
        "accent_hover": "#818CF8",
        "accent_active": "#4F46E5",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #818CF8, stop:1 #6366F1)",
        "accent_gradient_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A5B4FC, stop:1 #818CF8)",
        "accent_glow": "rgba(99, 102, 241, 0.20)",

        # 状态色
        "danger": "#EF4444",
        "danger_hover": "#F87171",
        "success": "#10B981",
        "warning": "#F59E0B",

        # === 圆角系统 ===
        "radius_xs": "6px",
        "radius_sm": "8px",
        "radius_md": "12px",
        "radius_lg": "16px",
        "radius_xl": "20px",
        "radius_pill": "8px",

        # === 其他 ===
        "border": "rgba(0, 0, 0, 0.06)",
        "separator": "rgba(0, 0, 0, 0.05)",
        "text_sec": "rgba(31, 41, 55, 0.55)",
        "list_bg": "rgba(249, 250, 251, 0.60)",
        "list_item_hover": "rgba(0, 0, 0, 0.03)",
        "list_item_selected": "rgba(99, 102, 241, 0.15)",

        # === GroupBox ===
        "card_bg": "rgba(249, 250, 251, 0.50)",
        "card_border": "rgba(0, 0, 0, 0.04)",
    },

    "Dark": {
        # ============================================
        # Dark Mode - 深邃优雅
        # ============================================

        # === 全局背景 ===
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0F0F11, stop:0.5 #16161A, stop:1 #0F0F11)",
        "bg_vibrancy": "rgba(15, 15, 17, 0.95)",

        # === 毛玻璃面板 ===
        "glass_bg": "rgba(30, 30, 35, 0.70)",
        "glass_gradient_start": "rgba(38, 38, 42, 0.80)",
        "glass_gradient_end": "rgba(26, 26, 30, 0.60)",
        "glass_bg_hover": "rgba(38, 38, 42, 0.80)",
        "glass_bg_strong": "rgba(42, 42, 47, 0.90)",

        # === 边框与高光 ===
        "glass_border": "rgba(255, 255, 255, 0.08)",
        "glass_border_bottom": "rgba(255, 255, 255, 0.04)",
        "glass_border_subtle": "rgba(255, 255, 255, 0.06)",
        "glass_border_dark": "rgba(0, 0, 0, 0.30)",

        # === 阴影系统 ===
        "shadow_sm": "0 1px 3px rgba(0, 0, 0, 0.25)",
        "shadow_glass": "0 4px 16px rgba(0, 0, 0, 0.30), 0 1px 2px rgba(0, 0, 0, 0.20)",
        "shadow_md": "0 2px 8px rgba(0, 0, 0, 0.25)",
        "shadow_lg": "0 4px 24px rgba(0, 0, 0, 0.30)",
        "shadow_xl": "0 8px 32px rgba(0, 0, 0, 0.35)",
        "shadow_glow": "0 2px 8px rgba(129, 140, 248, 0.20)",
        "shadow_primary_btn": "0 2px 4px rgba(129, 140, 248, 0.30)",

        # === 侧边栏 ===
        "sidebar": "rgba(22, 22, 26, 0.80)",
        "sidebar_hover": "rgba(255, 255, 255, 0.05)",
        "sidebar_active": "rgba(129, 140, 248, 0.15)",
        "sidebar_active_border": "rgba(129, 140, 248, 0.30)",
        "sidebar_pill_radius": "8px",

        # === 内容面板 ===
        "panel": "rgba(28, 28, 32, 0.65)",
        "panel_elevated": "rgba(35, 35, 40, 0.80)",
        "panel_border": "rgba(255, 255, 255, 0.06)",

        # === 拖拽区域 ===
        "dropzone_bg": "rgba(28, 28, 32, 0.50)",
        "dropzone_border": "rgba(129, 140, 248, 0.20)",
        "dropzone_border_dash": "rgba(255, 255, 255, 0.08)",
        "dropzone_hover_bg": "rgba(129, 140, 248, 0.08)",

        # === 输入控件 ===
        "input_bg": "rgba(0, 0, 0, 0.20)",
        "input_bg_focus": "rgba(45, 45, 50, 0.80)",
        "input_border": "rgba(255, 255, 255, 0.08)",
        "input_border_focus": "rgba(129, 140, 248, 0.50)",
        "input_shadow_inset": "inset 0 1px 2px rgba(0, 0, 0, 0.20)",
        "input_radius": "8px",

        # === 色彩系统 ===
        "fg": "#F9FAFB",
        "fg_secondary": "rgba(249, 250, 251, 0.65)",
        "fg_tertiary": "rgba(249, 250, 251, 0.45)",
        "fg_muted": "rgba(249, 250, 251, 0.35)",

        # 主色调：紫蓝色
        "accent": "#818CF8",
        "accent_hover": "#A5B4FC",
        "accent_active": "#6366F1",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #A5B4FC, stop:1 #818CF8)",
        "accent_gradient_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #C7D2FE, stop:1 #A5B4FC)",
        "accent_glow": "rgba(129, 140, 248, 0.25)",

        # 状态色
        "danger": "#F87171",
        "danger_hover": "#FCA5A5",
        "success": "#34D399",
        "warning": "#FBBF24",

        # === 圆角系统 ===
        "radius_xs": "6px",
        "radius_sm": "8px",
        "radius_md": "12px",
        "radius_lg": "16px",
        "radius_xl": "20px",
        "radius_pill": "8px",

        # === 其他 ===
        "border": "rgba(255, 255, 255, 0.08)",
        "separator": "rgba(255, 255, 255, 0.06)",
        "text_sec": "rgba(249, 250, 251, 0.55)",
        "list_bg": "rgba(35, 35, 40, 0.50)",
        "list_item_hover": "rgba(255, 255, 255, 0.04)",
        "list_item_selected": "rgba(129, 140, 248, 0.20)",

        # === GroupBox ===
        "card_bg": "rgba(0, 0, 0, 0.15)",
        "card_border": "rgba(255, 255, 255, 0.05)",
    },

    "Graphite": {
        # ============================================
        # Graphite - 经典石墨灰
        # ============================================

        # === 全局背景 ===
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #E8E9EB, stop:0.5 #E2E4E7, stop:1 #DCDDE1)",
        "bg_vibrancy": "rgba(232, 233, 235, 0.95)",

        # === 毛玻璃面板 ===
        "glass_bg": "rgba(255, 255, 255, 0.75)",
        "glass_gradient_start": "rgba(255, 255, 255, 0.82)",
        "glass_gradient_end": "rgba(245, 245, 248, 0.68)",
        "glass_bg_hover": "rgba(255, 255, 255, 0.85)",
        "glass_bg_strong": "rgba(255, 255, 255, 0.90)",

        # === 边框与高光 ===
        "glass_border": "rgba(0, 0, 0, 0.08)",
        "glass_border_bottom": "rgba(0, 0, 0, 0.04)",
        "glass_border_subtle": "rgba(0, 0, 0, 0.05)",
        "glass_border_dark": "rgba(0, 0, 0, 0.05)",

        # === 阴影系统 ===
        "shadow_sm": "0 1px 3px rgba(0, 0, 0, 0.05)",
        "shadow_glass": "0 4px 16px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
        "shadow_md": "0 2px 8px rgba(0, 0, 0, 0.06)",
        "shadow_lg": "0 4px 24px rgba(0, 0, 0, 0.07)",
        "shadow_xl": "0 8px 32px rgba(0, 0, 0, 0.08)",
        "shadow_glow": "0 2px 8px rgba(75, 85, 99, 0.15)",
        "shadow_primary_btn": "0 2px 4px rgba(75, 85, 99, 0.20)",

        # === 侧边栏 ===
        "sidebar": "rgba(240, 241, 245, 0.90)",
        "sidebar_hover": "rgba(0, 0, 0, 0.04)",
        "sidebar_active": "rgba(75, 85, 99, 0.12)",
        "sidebar_active_border": "rgba(75, 85, 99, 0.25)",
        "sidebar_pill_radius": "8px",

        # === 内容面板 ===
        "panel": "rgba(255, 255, 255, 0.65)",
        "panel_elevated": "rgba(255, 255, 255, 0.80)",
        "panel_border": "rgba(0, 0, 0, 0.06)",

        # === 拖拽区域 ===
        "dropzone_bg": "rgba(245, 246, 250, 0.60)",
        "dropzone_border": "rgba(75, 85, 99, 0.20)",
        "dropzone_border_dash": "rgba(0, 0, 0, 0.10)",
        "dropzone_hover_bg": "rgba(75, 85, 99, 0.06)",

        # === 输入控件 ===
        "input_bg": "rgba(245, 246, 250, 0.80)",
        "input_bg_focus": "rgba(255, 255, 255, 0.90)",
        "input_border": "rgba(0, 0, 0, 0.08)",
        "input_border_focus": "rgba(75, 85, 99, 0.40)",
        "input_shadow_inset": "inset 0 1px 2px rgba(0, 0, 0, 0.03)",
        "input_radius": "8px",

        # === 色彩系统 ===
        "fg": "#1F2937",
        "fg_secondary": "rgba(31, 41, 55, 0.60)",
        "fg_tertiary": "rgba(31, 41, 55, 0.40)",
        "fg_muted": "rgba(31, 41, 55, 0.30)",

        # 主色调：石墨灰
        "accent": "#4B5563",
        "accent_hover": "#6B7280",
        "accent_active": "#374151",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6B7280, stop:1 #4B5563)",
        "accent_gradient_hover": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7C8490, stop:1 #5B6370)",
        "accent_glow": "rgba(75, 85, 99, 0.15)",

        # 状态色
        "danger": "#DC2626",
        "danger_hover": "#EF4444",
        "success": "#059669",
        "warning": "#D97706",

        # === 圆角系统 ===
        "radius_xs": "6px",
        "radius_sm": "8px",
        "radius_md": "12px",
        "radius_lg": "16px",
        "radius_xl": "20px",
        "radius_pill": "8px",

        # === 其他 ===
        "border": "rgba(0, 0, 0, 0.06)",
        "separator": "rgba(0, 0, 0, 0.05)",
        "text_sec": "rgba(31, 41, 55, 0.55)",
        "list_bg": "rgba(240, 241, 245, 0.60)",
        "list_item_hover": "rgba(0, 0, 0, 0.03)",
        "list_item_selected": "rgba(75, 85, 99, 0.12)",

        # === GroupBox ===
        "card_bg": "rgba(245, 246, 250, 0.50)",
        "card_border": "rgba(0, 0, 0, 0.04)",
    }
}