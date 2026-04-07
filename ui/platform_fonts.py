import sys


def get_system_font_family():
    if sys.platform == "win32":
        return "Segoe UI"
    if sys.platform == "darwin":
        return "PingFang SC"  # macOS 中文字体，兼容性好
    return "Ubuntu"


def get_monospace_font_family():
    if sys.platform == "win32":
        return "Consolas"
    if sys.platform == "darwin":
        return "Menlo"
    return "DejaVu Sans Mono"


def get_system_font_qss():
    return f"'{get_system_font_family()}', sans-serif"


def get_monospace_font_qss():
    return f"'{get_monospace_font_family()}', monospace"
