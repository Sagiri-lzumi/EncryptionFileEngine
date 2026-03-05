import os


def ensure_long_path(path):
    """修复 Windows 路径过长问题"""
    if os.name == 'nt':
        try:
            path = os.path.abspath(path)
            if not path.startswith('\\\\?\\'):
                return f"\\\\?\\{path}"
        except Exception:
            return path
    return path


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


def get_drive_root(path):
    """获取驱动器根目录"""
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        parent = os.path.dirname(path)
        if parent == path:
            return parent
        path = parent
    return path
