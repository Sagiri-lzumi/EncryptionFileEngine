import os
import time
import hashlib
import multiprocessing
import shutil
import base64
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QAbstractItemView,
                               QFrame, QStackedWidget, QApplication, QCheckBox,
                               QSplitter, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import (QThread, Signal, Qt, QUrl, QPropertyAnimation,
                            QEasingCurve, QRectF, QSize, Property, QPoint, QParallelAnimationGroup)
from PySide6.QtGui import (QDesktopServices, QPainter, QColor, QPen, QFont,
                           QBrush, QIcon, QPainterPath, QCursor)

from config import DIRS
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger


# ==========================================
# 0. 核心修复：长路径处理工具函数
# ==========================================
def ensure_long_path(path):
    r"""
    修复 Windows 路径过长导致 WinError 123/206 的问题。
    原理：为绝对路径添加 \\?\ 前缀，解锁 32767 字符限制。
    注意：使用此前缀后，路径分隔符必须是反斜杠 \。
    """
    if os.name == 'nt':
        try:
            # 转换为绝对路径，这会自动将 / 转换为 \
            path = os.path.abspath(path)
            if not path.startswith('\\\\?\\'):
                return f"\\\\?\\{path}"
        except Exception:
            return path
    return path


# ==========================================
# 1. 配色方案 (包含白色主题)
# ==========================================
THEMES = {
    "Deep Space": {  # 深色默认
        "bg": "#121212", "sidebar": "#1a1a1a", "panel": "#242424",
        "border": "#383838", "fg": "#e0e0e0", "text_sec": "#9e9e9e",
        "accent": "#5c6bc0", "accent_hover": "#7986cb",
        "danger": "#ef5350", "input_bg": "#2c2c2c", "list_bg": "#1a1a1a",
        "shadow": "rgba(0,0,0,0.5)"
    },
    "Polaris": {  # 白色清爽 (回归)
        "bg": "#f0f2f5", "sidebar": "#ffffff", "panel": "#ffffff",
        "border": "#dce3e8", "fg": "#2c3e50", "text_sec": "#7f8c8d",
        "accent": "#007bff", "accent_hover": "#3395ff",
        "danger": "#ff4d4d", "input_bg": "#f7f9fa", "list_bg": "#ffffff",
        "shadow": "rgba(0,0,0,0.08)"
    },
    "Cyber Punk": {  # 赛博朋克
        "bg": "#0b0c15", "sidebar": "#151725", "panel": "#1c1f2e",
        "border": "#2a2d3e", "fg": "#e0e6ed", "text_sec": "#6c757d",
        "accent": "#ff0055", "accent_hover": "#ff3377",
        "danger": "#ff2a2a", "input_bg": "#151725", "list_bg": "#151725",
        "shadow": "rgba(255,0,85,0.15)"
    }
}

# 纯白加粗对钩 SVG (优化版)
CHECK_ICON = "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"white\" stroke-width=\"4\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><polyline points=\"20 6 9 17 4 12\"></polyline></svg>')"


# ==========================================
# 2. 自定义 UI 组件
# ==========================================

class AnimatedSidebarButton(QPushButton):
    """带动画效果的侧边栏按钮"""

    def __init__(self, text, icon_emoji, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(55)
        self.icon_emoji = icon_emoji
        self.setFont(QFont("Segoe UI", 10, QFont.Bold))

        # 动画属性
        self._hover_progress = 0.0
        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, v):
        self._hover_progress = v
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        theme = self.window().theme_data if hasattr(self.window(), 'theme_data') else THEMES["Deep Space"]

        is_checked = self.isChecked()

        # 背景绘制
        bg_color = QColor(theme['accent'])
        if is_checked:
            bg_color.setAlpha(40)  # 选中态淡色背景
        else:
            # 悬停态：根据 hover_progress 混合颜色
            alpha = int(20 * self._hover_progress)
            bg_color = QColor(theme['fg'])
            bg_color.setAlpha(alpha)

        if is_checked or self._hover_progress > 0.01:
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(8, 4, -8, -4), 8, 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_color)
            painter.drawPath(path)

        # 选中指示条 (左侧)
        if is_checked:
            bar_rect = QRectF(8, 12, 4, 31)
            painter.setBrush(QColor(theme['accent']))
            painter.drawRoundedRect(bar_rect, 2, 2)

        # 文字与图标
        text_color = QColor(theme['accent']) if is_checked else QColor(theme['text_sec'])
        if not is_checked and self._hover_progress > 0.5:
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
    """通用操作按钮"""

    def __init__(self, text="", color_type="normal", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.color_type = color_type
        self.setMinimumHeight(38)
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))

    def update_theme(self, theme):
        if self.color_type == "primary":
            base = theme['accent']
            hover = theme['accent_hover']
            text = "#ffffff"
            border = theme['accent']
        elif self.color_type == "danger":
            base = theme['danger']
            hover = QColor(theme['danger']).lighter(110).name()
            text = "#ffffff"
            border = theme['danger']
        else:
            base = theme['panel']
            hover = QColor(theme['panel']).lighter(120).name() if theme['bg'] == "#121212" else "#e0e0e0"
            text = theme['fg']
            border = theme['border']

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {hover};
                border-color: {hover};
            }}
            QPushButton:pressed {{
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background-color: {theme['bg']};
                color: {theme['text_sec']};
                border-color: {theme['border']};
            }}
        """)


class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.theme_data = THEMES["Deep Space"]

    def update_theme(self, theme_data):
        self.theme_data = theme_data
        self.viewport().update()

    def dragEnterEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dragMoveEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dropEvent(self, e):
        """
        修复：拖拽文件夹时，递归遍历文件夹下的所有文件并添加
        """
        if e.mimeData().hasUrls():
            e.accept()
            added = False
            existing_files = set([self.item(i).text() for i in range(self.count())])

            for url in e.mimeData().urls():
                path = url.toLocalFile()

                # 递归查找文件
                files_to_add = []
                if os.path.isfile(path):
                    files_to_add.append(path)
                elif os.path.isdir(path):
                    # 如果是文件夹，遍历所有子文件
                    for root, _, files in os.walk(path):
                        for file in files:
                            files_to_add.append(os.path.join(root, file))

                # 添加到列表
                for f_path in files_to_add:
                    # 规范化路径
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
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.viewport().rect().adjusted(10, 10, -10, -10)

            pen = QPen(QColor(self.theme_data["text_sec"]))
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, 8, 8)

            painter.drawText(self.viewport().rect(), Qt.AlignCenter, "📂 拖拽文件或文件夹到此处")
            painter.restore()


# ================= 辅助函数 =================
ENC_PREFIX = "ENC_DIR_"


def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


def get_drive_root(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        parent = os.path.dirname(path)
        if parent == path: return parent
        path = parent
    return path


def encrypt_dir_name_str(dir_name):
    try:
        if dir_name.startswith(ENC_PREFIX): return dir_name
        encoded = base64.urlsafe_b64encode(dir_name.encode()).decode()
        return f"{ENC_PREFIX}{encoded}"
    except:
        return dir_name


def decrypt_dir_name_str(dir_name):
    if dir_name.startswith(ENC_PREFIX):
        try:
            encoded = dir_name[len(ENC_PREFIX):]
            return base64.urlsafe_b64decode(encoded.encode()).decode()
        except:
            return dir_name
    return dir_name


# ================= 任务处理逻辑 =================
def task_wrapper(file_path, target_full_path, key_bytes, is_enc, enc_name, queue, stop_event, pause_event):
    from core.file_cipher import FileCipherEngine
    import time
    class MPController:
        def is_stop_requested(self): return stop_event.is_set()

        def wait_if_paused(self): pause_event.wait()

    last_update = 0

    def mp_callback(current, total):
        nonlocal last_update
        now = time.time()
        if now - last_update > 0.05 or current == total:
            queue.put(("PROGRESS", file_path, current, total))
            last_update = now

    engine = FileCipherEngine()
    try:
        # 修复点：使用长路径前缀
        f_path_long = ensure_long_path(file_path)
        t_path_long = ensure_long_path(target_full_path)

        queue.put(("START", file_path, os.path.getsize(f_path_long)))

        success, msg, out_path = engine.process_file_direct(
            f_path_long, t_path_long, key_bytes, is_enc,
            encrypt_filename=enc_name, callback=mp_callback, controller=MPController()
        )
        return (file_path, success, msg, out_path)
    except Exception as e:
        return (file_path, False, str(e), "")


class BatchWorkerThread(QThread):
    sig_progress = Signal(str, int)
    sig_log = Signal(str)
    sig_finished = Signal(dict)

    def __init__(self, files, key, is_encrypt, encrypt_filename=False,
                 custom_out_dir=None, keep_structure=False, encrypt_dirname=False,
                 use_ssd=False, ssd_dir=None):
        super().__init__()
        self.files = files
        self.key = key
        self.is_enc = is_encrypt
        self.enc_name = encrypt_filename
        self.custom_out = custom_out_dir
        self.keep_structure = keep_structure
        self.encrypt_dirname = encrypt_dirname
        self.use_ssd = use_ssd
        self.ssd_dir = ssd_dir
        self.manager = multiprocessing.Manager()
        self.queue = self.manager.Queue()
        self.stop_event = self.manager.Event()
        self.pause_event = self.manager.Event()
        self.pause_event.set()
        self._is_running = True

    def pause(self):
        self.pause_event.clear()

    def resume(self):
        self.pause_event.set()

    def stop(self):
        self.stop_event.set()
        self._is_running = False

    def run(self):
        key_bytes = hashlib.sha256(self.key.encode()).digest()
        results = {"success": [], "fail": []}
        valid_files = []
        total_bytes = 0
        self.processed_bytes_map = {}
        common_base = ""

        if self.keep_structure and len(self.files) > 0:
            try:
                common_base = os.path.commonpath(self.files)
                if os.path.isfile(common_base): common_base = os.path.dirname(common_base)
            except:
                pass

        self.sig_log.emit("--- 正在扫描任务队列 ---")
        for f in self.files:
            # 修复点：检查文件存在时使用长路径
            f_long = ensure_long_path(f)
            if os.path.exists(f_long):
                # 再次确认不是文件夹（虽然拖拽逻辑已过滤，但双重保险）
                if os.path.isfile(f_long):
                    s = os.path.getsize(f_long)
                    total_bytes += s
                    valid_files.append(f)
                    self.processed_bytes_map[f] = 0
            else:
                results["fail"].append((f, "文件不存在"))

        if not valid_files:
            self.sig_finished.emit(results)
            return

        temp_stage_root = None
        working_root_base = None

        if self.use_ssd and self.ssd_dir:
            try:
                drive_root = get_drive_root(self.ssd_dir)
                # 修复点：SSD 临时目录使用长路径
                temp_stage_root = os.path.join(drive_root, "_SSD_ENCRYPT_STAGE_TEMP")
                temp_stage_root = ensure_long_path(temp_stage_root)

                usage = shutil.disk_usage(self.ssd_dir)
                required = total_bytes * 1.2
                if usage.free < required:
                    self.sig_log.emit(f"⚠️ SSD 空间不足! 需 {format_size(required)}, 余 {format_size(usage.free)}")
                    self.use_ssd = False
                    working_root_base = self.custom_out
                else:
                    self.sig_log.emit(f"✅ [SSD 加速] 已启用。暂存区: {temp_stage_root}")
                    if os.path.exists(temp_stage_root): shutil.rmtree(temp_stage_root, ignore_errors=True)
                    os.makedirs(temp_stage_root, exist_ok=True)
                    working_root_base = temp_stage_root
            except Exception as e:
                self.sig_log.emit(f"❌ SSD 检测出错: {e}, 已禁用加速")
                self.use_ssd = False
                working_root_base = self.custom_out
        else:
            working_root_base = self.custom_out

        max_workers = min(os.cpu_count(), len(valid_files))
        if self.use_ssd: max_workers = max(max_workers, 4)
        self.sig_log.emit(f"🚀 启动 {max_workers} 个加密核心...")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for f_path in valid_files:
                if not self.use_ssd and not self.custom_out:
                    current_base = os.path.dirname(f_path)
                else:
                    current_base = working_root_base

                rel_path_struct = ""
                if self.keep_structure and common_base:
                    try:
                        rel = os.path.relpath(os.path.dirname(f_path), common_base)
                        if rel == ".": rel = ""
                        parts = rel.split(os.sep)
                        processed_parts = []
                        for p in parts:
                            if not p: continue
                            if self.is_enc:
                                processed_parts.append(encrypt_dir_name_str(p) if self.encrypt_dirname else p)
                            else:
                                processed_parts.append(decrypt_dir_name_str(p))
                        rel_path_struct = os.sep.join(processed_parts)
                    except:
                        rel_path_struct = ""

                final_out_dir = os.path.join(current_base, rel_path_struct)
                fname = os.path.basename(f_path)
                target_file_path = os.path.join(final_out_dir, fname + ".enc" if self.is_enc else fname)

                futures.append(executor.submit(
                    task_wrapper, f_path, target_file_path, key_bytes, self.is_enc, self.enc_name,
                    self.queue, self.stop_event, self.pause_event
                ))

            finished_count = 0
            prog_factor = 0.6 if self.use_ssd else 1.0

            while finished_count < len(valid_files) and self._is_running:
                try:
                    while not self.queue.empty():
                        msg_type, *data = self.queue.get_nowait()
                        if msg_type == "PROGRESS":
                            fp, curr, _ = data
                            self.processed_bytes_map[fp] = curr
                except:
                    pass
                QThread.msleep(50)
                done = sum(self.processed_bytes_map.values())
                if total_bytes > 0:
                    pct = int((done / total_bytes) * 100 * prog_factor)
                    self.sig_progress.emit(f"正在处理... {pct}%", pct)

                done_futures = [f for f in futures if f.done()]
                if len(done_futures) > finished_count:
                    for f in done_futures:
                        if getattr(f, '_handled', False): continue
                        f._handled = True
                        finished_count += 1
                        try:
                            fp, success, msg, outp = f.result()
                            if success:
                                results["success"].append((fp, outp))
                                self.sig_log.emit(f"✅ {os.path.basename(fp)}")
                            else:
                                results["fail"].append((fp, msg))
                                self.sig_log.emit(f"❌ {os.path.basename(fp)}: {msg}")
                        except Exception as e:
                            self.sig_log.emit(f"❌ 异常: {e}")

            if not self._is_running: executor.shutdown(wait=False, cancel_futures=True)

        if self.use_ssd and self._is_running and temp_stage_root:
            self.sig_log.emit("--- ⚡ SSD 高速回写 ---")
            try:
                final_dest_root = self.custom_out
                if not final_dest_root: final_dest_root = common_base if common_base else os.path.dirname(self.files[0])

                # 修复点：回写目标目录也需要长路径
                final_dest_root = ensure_long_path(final_dest_root)
                if not os.path.exists(final_dest_root): os.makedirs(final_dest_root, exist_ok=True)

                items = os.listdir(temp_stage_root)
                total_stage_bytes = 0
                for item in items:
                    src_p = os.path.join(temp_stage_root, item)
                    # 修复点：获取大小时使用长路径
                    src_p_long = ensure_long_path(src_p)
                    if os.path.isfile(src_p_long):
                        total_stage_bytes += os.path.getsize(src_p_long)
                    elif os.path.isdir(src_p_long):
                        for root, _, fs in os.walk(src_p_long):
                            for f in fs: total_stage_bytes += os.path.getsize(os.path.join(root, f))
                if total_stage_bytes == 0: total_stage_bytes = 1
                moved_bytes = 0
                for item in items:
                    if not self._is_running: break
                    src_item = os.path.join(temp_stage_root, item)
                    dst_item = os.path.join(final_dest_root, item)

                    # 修复点：检查目标是否存在时使用长路径
                    dst_item_long = ensure_long_path(dst_item)
                    if os.path.exists(dst_item_long):
                        if os.path.isdir(dst_item_long):
                            shutil.rmtree(dst_item_long)
                        else:
                            os.remove(dst_item_long)
                    moved_bytes = self._manual_move(src_item, dst_item, moved_bytes, total_stage_bytes)
                shutil.rmtree(temp_stage_root)
                self.sig_log.emit("✅ 回写完成")
            except Exception as e:
                self.sig_log.emit(f"❌ 回写失败: {e}")

        msg = "任务完成" if self._is_running else "已终止"
        self.sig_progress.emit(msg, 100)
        self.sig_finished.emit(results)

    def _manual_move(self, src, dst, current_moved_total, total_stage_bytes):
        try:
            # 修复点：所有文件操作都包裹 ensure_long_path
            src_long = ensure_long_path(src)
            dst_long = ensure_long_path(dst)

            src_dev = os.stat(src_long).st_dev
            dst_dir = os.path.dirname(dst_long)
            if not os.path.exists(dst_dir): os.makedirs(dst_dir, exist_ok=True)
            dst_dev = os.stat(dst_dir).st_dev
            is_dir = os.path.isdir(src_long)

            if src_dev == dst_dev:
                shutil.move(src_long, dst_long)
                if is_dir:
                    size = 0
                    for r, _, fs in os.walk(dst_long):
                        for f in fs: size += os.path.getsize(os.path.join(r, f))
                    return current_moved_total + size
                else:
                    return current_moved_total + os.path.getsize(dst_long)

            if is_dir:
                shutil.move(src_long, dst_long)
                size = 0
                for r, _, fs in os.walk(dst_long):
                    for f in fs: size += os.path.getsize(os.path.join(r, f))
                return current_moved_total + size
            else:
                chunk_size = 10 * 1024 * 1024
                with open(src_long, 'rb') as fsrc, open(dst_long, 'wb') as fdst:
                    while True:
                        if not self._is_running: raise InterruptedError("Stopped")
                        buf = fsrc.read(chunk_size)
                        if not buf: break
                        fdst.write(buf)
                        current_moved_total += len(buf)
                        pct = 60 + int((current_moved_total / total_stage_bytes) * 40)
                        pct = min(pct, 99)
                        self.sig_progress.emit(f"回写数据... {pct}%", pct)
                os.remove(src_long)
                # shutil.copystat 可能会因为长路径问题报错，这里加个 try
                try:
                    if os.path.exists(src_long): shutil.copystat(src_long, dst_long)
                except:
                    pass
                return current_moved_total
        except Exception as e:
            # 尝试最后的 fallback
            try:
                src_long = ensure_long_path(src)
                dst_long = ensure_long_path(dst)
                if os.path.exists(src_long) and not os.path.exists(dst_long):
                    shutil.move(src_long, dst_long)
                    return current_moved_total + os.path.getsize(dst_long)
            except:
                pass
            return current_moved_total


# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Security Engine Enterprise")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 650)

        # 主题管理
        self.theme_names = list(THEMES.keys())
        self.current_theme_idx = 0
        self.theme_data = THEMES[self.theme_names[0]]

        self.custom_enc_path = None
        self.custom_dec_path = None
        self.custom_ssd_path = None
        self.last_out_dir = ""
        self.is_paused = False
        self.worker = None
        self.all_buttons = []
        self.sidebar_btns = []

        self._init_ui()
        self.apply_theme()

    def _init_ui(self):
        # 主容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 1. 左侧导航栏 ===
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setObjectName("Sidebar")

        v_sidebar = QVBoxLayout(self.sidebar)
        v_sidebar.setContentsMargins(15, 30, 15, 30)
        v_sidebar.setSpacing(15)

        # 标题
        lbl_title = QLabel("🛡️ 安全引擎")
        lbl_title.setObjectName("AppTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setFixedHeight(60)
        v_sidebar.addWidget(lbl_title)

        v_sidebar.addSpacing(20)

        # 导航按钮
        self.btn_nav_enc = AnimatedSidebarButton("加密终端", "🔒", self)
        self.btn_nav_dec = AnimatedSidebarButton("解密终端", "🔓", self)
        self.btn_nav_log = AnimatedSidebarButton("日志审计", "📜", self)

        self.btn_nav_enc.setChecked(True)  # 默认选中

        # 按钮组逻辑
        self.btn_nav_enc.clicked.connect(lambda: self.switch_page(0))
        self.btn_nav_dec.clicked.connect(lambda: self.switch_page(1))
        self.btn_nav_log.clicked.connect(lambda: self.switch_page(2))

        self.sidebar_btns = [self.btn_nav_enc, self.btn_nav_dec, self.btn_nav_log]
        for btn in self.sidebar_btns:
            v_sidebar.addWidget(btn)

        v_sidebar.addStretch()

        # 底部主题切换
        self.btn_theme = ModernButton("主题: Deep Space", "normal")
        self.btn_theme.clicked.connect(self.cycle_theme)
        self.all_buttons.append(self.btn_theme)
        v_sidebar.addWidget(self.btn_theme)

        main_layout.addWidget(self.sidebar)

        # === 2. 右侧内容区 ===
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        self._init_page_encrypt()
        self._init_page_decrypt()
        self._init_page_log()

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        # 更新按钮状态
        for i, btn in enumerate(self.sidebar_btns):
            btn.setChecked(i == index)
            btn.update()  # 强制重绘

    def _create_common_layout(self, is_encrypt):
        page = QWidget()
        # 使用 Splitter 允许用户调整左右比例
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # === 左侧：文件列表 (Card) ===
        left_container = QFrame()
        left_container.setObjectName("ContentPanel")
        v_left = QVBoxLayout(left_container)
        v_left.setContentsMargins(20, 20, 20, 20)
        v_left.setSpacing(15)

        lbl_list = QLabel("📄 待处理文件队列")
        lbl_list.setObjectName("SectionTitle")
        v_left.addWidget(lbl_list)

        file_list = DragDropListWidget()
        v_left.addWidget(file_list)

        # 按钮栏
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_add = ModernButton("➕ 添加文件", "normal")
        btn_add.clicked.connect(lambda: self.action_add_file(is_encrypt))
        self.all_buttons.append(btn_add)

        # 新增：添加目录按钮
        btn_add_folder = ModernButton("➕ 添加目录", "normal")
        btn_add_folder.clicked.connect(lambda: self.action_add_folder(is_encrypt))
        self.all_buttons.append(btn_add_folder)

        btn_del = ModernButton("➖ 移除选中", "normal")
        btn_del.clicked.connect(lambda: self.action_remove_file(file_list, is_encrypt))
        self.all_buttons.append(btn_del)

        btn_clr = ModernButton("🗑️ 清空", "normal")
        btn_clr.clicked.connect(lambda: (file_list.clear(), self.reset_ui_state(is_encrypt)))
        self.all_buttons.append(btn_clr)

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_add_folder)  # 添加到布局
        btn_bar.addWidget(btn_del)
        btn_bar.addWidget(btn_clr)
        btn_bar.addStretch()

        v_left.addLayout(btn_bar)
        splitter.addWidget(left_container)

        # === 右侧：配置面板 (Card) ===
        right_container = QFrame()
        right_container.setObjectName("ContentPanel")
        right_container.setMinimumWidth(400)
        right_container.setMaximumWidth(500)

        v_right = QVBoxLayout(right_container)
        v_right.setContentsMargins(20, 20, 20, 20)
        v_right.setSpacing(20)

        lbl_settings = QLabel("⚙️ 任务配置")
        lbl_settings.setObjectName("SectionTitle")
        v_right.addWidget(lbl_settings)

        # 1. 安全设置
        grp_sec = QGroupBox("安全凭证")
        v_sec = QVBoxLayout(grp_sec)
        v_sec.setSpacing(10)
        v_sec.setContentsMargins(15, 25, 15, 15)

        txt_pwd = QLineEdit()
        txt_pwd.setEchoMode(QLineEdit.Password)
        txt_pwd.setPlaceholderText("输入密钥...")
        v_sec.addWidget(txt_pwd)
        v_right.addWidget(grp_sec)

        # 2. 输出设置
        grp_io = QGroupBox("输出路径")
        v_io = QVBoxLayout(grp_io)
        v_io.setSpacing(10)
        v_io.setContentsMargins(15, 25, 15, 15)

        h_path = QHBoxLayout()
        txt_path = QLineEdit()
        txt_path.setPlaceholderText("默认：覆盖源文件")
        txt_path.setReadOnly(True)
        h_path.addWidget(txt_path)

        btn_path = ModernButton("...", "normal")
        btn_path.setFixedWidth(40)
        btn_path.clicked.connect(lambda: self.action_select_dir(is_encrypt))
        self.all_buttons.append(btn_path)
        h_path.addWidget(btn_path)
        v_io.addLayout(h_path)

        # 逻辑：只有选择了路径，才能勾选保留结构
        chk_struct = QCheckBox("保留目录结构")
        chk_struct.setEnabled(False)  # 默认禁用
        v_io.addWidget(chk_struct)

        chk_dir_name_enc = None
        if is_encrypt:
            # 逻辑：只有勾选了保留结构，才能勾选加密文件夹名
            chk_dir_name_enc = QCheckBox("加密文件夹名")
            chk_dir_name_enc.setEnabled(False)
            v_io.addWidget(chk_dir_name_enc)

            def on_struct_toggled(state):
                is_checked = (state == 2)
                if chk_dir_name_enc:
                    chk_dir_name_enc.setEnabled(is_checked)
                    if not is_checked: chk_dir_name_enc.setChecked(False)

            chk_struct.stateChanged.connect(on_struct_toggled)
        else:
            # 解密时同理
            chk_dir_name_enc = QCheckBox("解密文件夹名")
            chk_dir_name_enc.setEnabled(False)
            v_io.addWidget(chk_dir_name_enc)

            def on_struct_toggled_dec(state):
                is_checked = (state == 2)
                if chk_dir_name_enc:
                    chk_dir_name_enc.setEnabled(is_checked)
                    if not is_checked: chk_dir_name_enc.setChecked(False)

            chk_struct.stateChanged.connect(on_struct_toggled_dec)

        v_right.addWidget(grp_io)

        # 3. 高级选项
        grp_adv = QGroupBox("高级策略")
        v_adv = QVBoxLayout(grp_adv)
        v_adv.setSpacing(10)
        v_adv.setContentsMargins(15, 25, 15, 15)

        h_ssd = QHBoxLayout()
        txt_ssd = QLineEdit()
        txt_ssd.setPlaceholderText("请先选择缓存路径 ->")
        txt_ssd.setReadOnly(True)
        h_ssd.addWidget(txt_ssd)

        btn_ssd = ModernButton("选择缓存", "normal")
        btn_ssd.setFixedWidth(80)
        btn_ssd.clicked.connect(lambda: self.action_select_ssd(is_encrypt))
        self.all_buttons.append(btn_ssd)
        h_ssd.addWidget(btn_ssd)
        v_adv.addLayout(h_ssd)

        # 逻辑：只有选择了SSD路径，才能勾选启用
        chk_ssd = QCheckBox("启用 SSD 加速")
        chk_ssd.setEnabled(False)  # 默认禁用
        v_adv.addWidget(chk_ssd)

        chk_name = None
        chk_del = None
        if is_encrypt:
            chk_name = QCheckBox("混淆文件名")
            chk_name.setChecked(True)
            v_adv.addWidget(chk_name)
            chk_del = QCheckBox("完成后粉碎源文件")
            v_adv.addWidget(chk_del)
        else:
            chk_del = QCheckBox("解密后移除加密包")
            v_adv.addWidget(chk_del)

        v_right.addWidget(grp_adv)
        v_right.addStretch()

        # 状态与控制
        lbl_status = QLabel("就绪")
        lbl_status.setAlignment(Qt.AlignCenter)
        lbl_status.setObjectName("StatusLabel")
        v_right.addWidget(lbl_status)

        pbar = QProgressBar()
        pbar.setValue(0)
        pbar.setTextVisible(False)
        pbar.setFixedHeight(6)
        v_right.addWidget(pbar)

        stack = QStackedWidget()
        stack.setFixedHeight(50)

        # Start
        w_start = QWidget()
        l_start = QHBoxLayout(w_start)
        l_start.setContentsMargins(0, 0, 0, 0)
        btn_run = ModernButton(f"开始{'加密' if is_encrypt else '解密'}", "primary")
        btn_run.clicked.connect(self.run_encrypt if is_encrypt else self.run_decrypt)
        self.all_buttons.append(btn_run)
        l_start.addWidget(btn_run)
        stack.addWidget(w_start)

        # Running
        w_ctrl = QWidget()
        l_ctrl = QHBoxLayout(w_ctrl)
        l_ctrl.setContentsMargins(0, 0, 0, 0)
        btn_pause = ModernButton("挂起", "normal")
        btn_pause.clicked.connect(self.action_toggle_pause)
        self.all_buttons.append(btn_pause)
        btn_stop = ModernButton("终止", "danger")
        btn_stop.clicked.connect(self.action_stop_task)
        self.all_buttons.append(btn_stop)
        l_ctrl.addWidget(btn_pause)
        l_ctrl.addWidget(btn_stop)
        stack.addWidget(w_ctrl)

        # Finish
        w_res = QWidget()
        l_res = QHBoxLayout(w_res)
        l_res.setContentsMargins(0, 0, 0, 0)
        btn_open = ModernButton("打开目录", "normal")
        btn_open.clicked.connect(self.action_open_folder)
        self.all_buttons.append(btn_open)
        btn_back = ModernButton("返回", "normal")
        btn_back.clicked.connect(lambda: self.reset_ui_state(is_encrypt))
        self.all_buttons.append(btn_back)
        l_res.addWidget(btn_open)
        l_res.addWidget(btn_back)
        stack.addWidget(w_res)

        v_right.addWidget(stack)
        splitter.addWidget(right_container)

        # 设置 Splitter 比例
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        # 包装到 Layout
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(splitter)

        refs = {
            "list": file_list, "pwd": txt_pwd, "path": txt_path,
            "chk_name": chk_name, "chk_del": chk_del,
            "chk_struct": chk_struct, "chk_dir_name_enc": chk_dir_name_enc,
            "chk_ssd": chk_ssd, "txt_ssd": txt_ssd,
            "status": lbl_status, "pbar": pbar, "stack": stack,
            "btn_pause": btn_pause
        }
        return page, refs

    def _init_page_encrypt(self):
        page, refs = self._create_common_layout(True)
        self.ui_enc = refs
        self.content_stack.addWidget(page)

    def _init_page_decrypt(self):
        page, refs = self._create_common_layout(False)
        self.ui_dec = refs
        self.content_stack.addWidget(page)

    def _init_page_log(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("ContentPanel")
        v = QVBoxLayout(container)
        v.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("📜 系统运行日志")
        lbl.setObjectName("SectionTitle")
        v.addWidget(lbl)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("border: none; font-family: 'Consolas', monospace;")
        v.addWidget(self.txt_log)

        layout.addWidget(container)
        self.content_stack.addWidget(page)

    def cycle_theme(self):
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.theme_names)
        self.apply_theme()

    def apply_theme(self):
        theme_name = self.theme_names[self.current_theme_idx]
        t = THEMES[theme_name]
        self.theme_data = t

        self.btn_theme.setText(f"主题: {theme_name}")

        # 全局样式表
        qss = f"""
        QMainWindow, QWidget {{
            background-color: {t['bg']};
            color: {t['fg']};
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            font-size: 10pt;
        }}

        /* 侧边栏 */
        QFrame#Sidebar {{
            background-color: {t['sidebar']};
            border-right: 1px solid {t['border']};
        }}
        QLabel#AppTitle {{
            color: {t['fg']};
            font-size: 16pt;
            font-weight: bold;
        }}

        /* 内容卡片 */
        QFrame#ContentPanel {{
            background-color: {t['panel']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}

        QLabel#SectionTitle {{
            color: {t['accent']};
            font-size: 12pt;
            font-weight: bold;
            padding-bottom: 5px;
            border-bottom: 2px solid {t['accent']};
        }}

        QLabel#StatusLabel {{
            color: {t['text_sec']};
            font-weight: bold;
        }}

        /* 输入框 */
        QLineEdit, QTextEdit {{
            background-color: {t['input_bg']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            color: {t['fg']};
            padding: 8px;
            selection-background-color: {t['accent']};
        }}
        QLineEdit:focus {{
            border: 1px solid {t['accent']};
        }}
        QLineEdit:disabled {{
            color: {t['text_sec']};
            background-color: {t['bg']};
        }}

        /* GroupBox */
        QGroupBox {{
            border: 1px solid {t['border']};
            border-radius: 8px;
            margin-top: 10px;
            font-weight: bold;
            color: {t['text_sec']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
        }}

        /* 列表 */
        QListWidget {{
            background-color: {t['list_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            outline: none;
        }}
        QListWidget::item {{
            height: 36px;
            padding: 5px;
            border-bottom: 1px solid {t['border']};
        }}
        QListWidget::item:selected {{
            background-color: {t['accent']}33; /* 20% opacity */
            border-left: 3px solid {t['accent']};
            color: {t['fg']};
        }}

        /* 进度条 */
        QProgressBar {{
            background-color: {t['input_bg']};
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background-color: {t['accent']};
            border-radius: 3px;
        }}

        /* 勾选框美化 (核心修改) */
        QCheckBox {{
            spacing: 8px;
            color: {t['fg']};
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid {t['text_sec']};
            background: {t['input_bg']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {t['accent']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {t['accent']};
            border-color: {t['accent']};
            image: {CHECK_ICON};
        }}
        QCheckBox::indicator:disabled {{
            border-color: {t['border']};
            background-color: {t['bg']};
        }}
        QCheckBox:disabled {{
            color: {t['text_sec']};
        }}

        /* Splitter */
        QSplitter::handle {{
            background-color: {t['border']};
        }}
        """
        self.setStyleSheet(qss)

        # 更新自定义组件
        for btn in self.all_buttons:
            btn.update_theme(t)

        for btn in self.sidebar_btns:
            btn.update()  # 触发重绘

        self.ui_enc["list"].update_theme(t)
        self.ui_dec["list"].update_theme(t)

    # ================= 逻辑控制 (Strict Logic) =================
    def check_constraints(self):
        # 1. 输出路径 -> 保留目录结构
        enc_path = self.custom_enc_path
        if not enc_path:
            self.ui_enc["chk_struct"].setChecked(False)
            self.ui_enc["chk_struct"].setEnabled(False)
        else:
            self.ui_enc["chk_struct"].setEnabled(True)

        # 2. 保留目录结构 -> 加密文件夹名
        if self.ui_enc["chk_struct"].isChecked() and self.ui_enc["chk_dir_name_enc"]:
            self.ui_enc["chk_dir_name_enc"].setEnabled(True)
        else:
            if self.ui_enc["chk_dir_name_enc"]:
                self.ui_enc["chk_dir_name_enc"].setChecked(False)
                self.ui_enc["chk_dir_name_enc"].setEnabled(False)

        # 解密端同理
        dec_path = self.custom_dec_path
        if not dec_path:
            self.ui_dec["chk_struct"].setChecked(False)
            self.ui_dec["chk_struct"].setEnabled(False)
        else:
            self.ui_dec["chk_struct"].setEnabled(True)

        if self.ui_dec["chk_struct"].isChecked() and self.ui_dec["chk_dir_name_enc"]:
            self.ui_dec["chk_dir_name_enc"].setEnabled(True)
        else:
            if self.ui_dec["chk_dir_name_enc"]:
                self.ui_dec["chk_dir_name_enc"].setChecked(False)
                self.ui_dec["chk_dir_name_enc"].setEnabled(False)

        # 3. SSD 路径 -> 启用 SSD 加速
        # 加密端
        if self.custom_ssd_path:
            self.ui_enc["chk_ssd"].setEnabled(True)
            self.ui_dec["chk_ssd"].setEnabled(True)
        else:
            self.ui_enc["chk_ssd"].setChecked(False)
            self.ui_enc["chk_ssd"].setEnabled(False)
            self.ui_dec["chk_ssd"].setChecked(False)
            self.ui_dec["chk_ssd"].setEnabled(False)

    def action_add_file(self, is_encrypt):
        self.reset_ui_state(is_encrypt)
        ui = self.ui_enc if is_encrypt else self.ui_dec
        flter = "所有文件 (*)" if is_encrypt else "加密文件 (*.enc)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", flter)
        if files:
            existing = set([ui["list"].item(i).text() for i in range(ui["list"].count())])
            for f in files:
                if f not in existing: ui["list"].addItem(f)
            self.check_constraints()

    def action_add_folder(self, is_encrypt):
        """
        新增：添加目录功能，递归读取目录下所有文件
        """
        self.reset_ui_state(is_encrypt)
        ui = self.ui_enc if is_encrypt else self.ui_dec
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            existing = set([ui["list"].item(i).text() for i in range(ui["list"].count())])
            added = False
            for root, _, files in os.walk(d):
                for file in files:
                    full_path = os.path.normpath(os.path.join(root, file))
                    if full_path not in existing:
                        ui["list"].addItem(full_path)
                        existing.add(full_path)
                        added = True
            if added:
                self.check_constraints()

    def action_remove_file(self, lst, is_encrypt):
        self.reset_ui_state(is_encrypt)
        for item in lst.selectedItems():
            lst.takeItem(lst.row(item))
        self.check_constraints()

    def action_select_dir(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            if is_encrypt:
                self.custom_enc_path = d
                self.ui_enc["path"].setText(d)
            else:
                self.custom_dec_path = d
                self.ui_dec["path"].setText(d)
        self.check_constraints()

    def action_select_ssd(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择 SSD 缓存目录")
        if d:
            self.custom_ssd_path = d
            self.ui_enc["txt_ssd"].setText(d)
            self.ui_dec["txt_ssd"].setText(d)
        self.check_constraints()

    def reset_ui_state(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        ui["stack"].setCurrentIndex(0)
        ui["pbar"].setValue(0)
        ui["status"].setText("就绪")
        ui["list"].setEnabled(True)
        ui["pwd"].setEnabled(True)
        self.check_constraints()

    def run_encrypt(self):
        self._start_process(True)

    def run_decrypt(self):
        self._start_process(False)

    def _start_process(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        count = ui["list"].count()
        if count == 0: return QMessageBox.warning(self, "提示", "任务队列为空。")
        pwd = ui["pwd"].text()
        if not pwd: return QMessageBox.warning(self, "安全提示", "必须输入密钥。")

        files = [ui["list"].item(i).text() for i in range(count)]
        path = self.custom_enc_path if is_encrypt else self.custom_dec_path
        keep_struct = ui["chk_struct"].isChecked()
        enc_dirname = False
        if is_encrypt and ui["chk_dir_name_enc"]:
            enc_dirname = ui["chk_dir_name_enc"].isEnabled() and ui["chk_dir_name_enc"].isChecked()

        use_ssd = ui["chk_ssd"].isChecked()
        ssd_path = self.custom_ssd_path if use_ssd else None

        if use_ssd and (not ssd_path or not os.path.exists(ssd_path)):
            return QMessageBox.warning(self, "参数缺失", "请选择有效的 SSD 缓存目录。")

        ui["list"].setEnabled(False)
        ui["pwd"].setEnabled(False)
        ui["stack"].setCurrentIndex(1)
        ui["pbar"].setValue(0)
        ui["status"].setText("初始化引擎...")

        self.is_paused = False
        self.worker = BatchWorkerThread(
            files, pwd, is_encrypt,
            encrypt_filename=ui["chk_name"].isChecked() if is_encrypt and ui["chk_name"] else False,
            custom_out_dir=path, keep_structure=keep_struct, encrypt_dirname=enc_dirname,
            use_ssd=use_ssd, ssd_dir=ssd_path
        )

        self.worker.sig_progress.connect(self.update_progress)
        self.worker.sig_log.connect(self.append_log)
        self.worker.sig_finished.connect(lambda r: self.on_finished(r, is_encrypt))
        self.worker.start()

    def update_progress(self, text, val):
        if not self.worker: return
        is_enc_task = self.worker.is_enc
        ui = self.ui_enc if is_enc_task else self.ui_dec
        ui["status"].setText(text)
        ui["pbar"].setValue(val)

    def append_log(self, text):
        t = datetime.now().strftime("%H:%M:%S")
        color = self.theme_data['text_sec']
        self.txt_log.append(f"<span style='color:{color}'>[{t}]</span> {text}")
        sys_logger.log(text)

    def action_toggle_pause(self):
        if not self.worker: return
        is_enc_task = self.worker.is_enc
        ui = self.ui_enc if is_enc_task else self.ui_dec
        if self.is_paused:
            self.worker.resume()
            self.is_paused = False
            ui["btn_pause"].setText("挂起")
            ui["status"].setText("正在处理...")
        else:
            self.worker.pause()
            self.is_paused = True
            ui["btn_pause"].setText("继续")
            ui["status"].setText("已挂起")

    def action_stop_task(self):
        if self.worker:
            if self.is_paused: self.worker.resume()
            self.worker.stop()
            self.append_log(f"用户终止任务")

    def on_finished(self, results, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        ui["stack"].setCurrentIndex(2)
        ui["list"].setEnabled(True)
        ui["pwd"].setEnabled(True)
        ui["list"].clear()

        if results["success"]:
            self.last_out_dir = os.path.dirname(results["success"][0][1])

        chk_del = ui["chk_del"]
        if chk_del.isChecked():
            self.append_log("执行安全删除...")
            for src, _ in results["success"]:
                try:
                    os.remove(src)
                except:
                    pass

        succ = len(results["success"])
        fail = len(results["fail"])
        if fail == 0:
            QMessageBox.information(self, "完成", f"成功处理 {succ} 个文件")
        else:
            QMessageBox.warning(self, "完成", f"成功: {succ}, 失败: {fail}")

    def action_open_folder(self):
        if self.last_out_dir and os.path.exists(self.last_out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out_dir))
        else:
            QMessageBox.information(self, "提示", "目录不存在")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
