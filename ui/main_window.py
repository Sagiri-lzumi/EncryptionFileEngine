# -*- coding: utf-8 -*-
"""
Encryption Studio - 主窗口模块
==============================

本模块是应用程序的核心 UI 模块，包含以下主要组件：

1. MainWindow: 主窗口类，管理整体界面布局和用户交互
2. BatchWorkerThread: 后台任务处理线程，负责文件加密/解密的批量处理
3. 辅助函数: 目录名加密/解密、任务包装器等

架构说明：
- UI 与业务逻辑分离：所有耗时操作通过 QThread 在后台执行
- 信号槽机制：线程间通信使用 Qt Signal/Slot，保证线程安全
- 主题系统：支持多主题切换，样式通过 QSS 动态管理

作者：Encryption Studio Team
"""

import os
import time
import hashlib
import multiprocessing
import shutil
import base64
import binascii
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from queue import Queue, Empty

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QAbstractItemView,
                               QFrame, QStackedWidget, QApplication, QCheckBox,
                               QSplitter, QGraphicsDropShadowEffect, QSizePolicy,
                               QSystemTrayIcon, QMenu, QComboBox)
from PySide6.QtCore import (QThread, Signal, Qt, QUrl, QPropertyAnimation,
                            QEasingCurve, QRectF, QSize, Property, QPoint, QParallelAnimationGroup)
from PySide6.QtGui import (QDesktopServices, QPainter, QColor, QPen, QFont,
                           QBrush, QIcon, QPainterPath, QCursor, QAction)

from config import DIRS
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger
from ui.themes import THEMES
from ui.native_effects import NativeGlassController
from ui.components import AnimatedSidebarButton, ModernButton, DragDropListWidget, CustomCheckBox, ThemeSelector, SmoothScrollArea, DropDownComboBox, SystemSwitchButton, GlassProgressBar
from ui.platform_fonts import get_monospace_font_qss, get_system_font_family, get_system_font_qss
from ui.utils import ensure_long_path, format_size, get_drive_root


# ================= 辅助函数 =================
# 目录名加密前缀，用于标识已加密的目录名
ENC_PREFIX = "ENC_DIR_"


def encrypt_dir_name_str(dir_name):
    """
    加密目录名称

    使用 Base64 URL 安全编码对目录名进行加密，
    并添加前缀标识，便于后续识别和解密。

    参数:
        dir_name: 原始目录名称

    返回:
        加密后的目录名称（带前缀），如已加密则原样返回
    """
    try:
        if dir_name.startswith(ENC_PREFIX): return dir_name
        encoded = base64.urlsafe_b64encode(dir_name.encode()).decode()
        return f"{ENC_PREFIX}{encoded}"
    except (UnicodeEncodeError, ValueError):
        return dir_name


def decrypt_dir_name_str(dir_name):
    """
    解密目录名称

    识别带有加密前缀的目录名，并进行 Base64 解码还原。

    参数:
        dir_name: 可能已加密的目录名称

    返回:
        解密后的原始目录名称，如未加密则原样返回
    """
    if dir_name.startswith(ENC_PREFIX):
        try:
            encoded = dir_name[len(ENC_PREFIX):]
            return base64.urlsafe_b64decode(encoded.encode()).decode()
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return dir_name
    return dir_name


# ================= 任务处理逻辑 =================
def task_wrapper(file_path, target_full_path, key_bytes, is_enc, enc_name, queue, stop_event, pause_event):
    """
    任务包装器函数

    用于多进程/多线程环境下的单个文件处理任务。
    封装文件加密/解密操作，并通过队列报告进度。

    参数:
        file_path: 源文件路径
        target_full_path: 目标文件路径
        key_bytes: 加密密钥（32字节）
        is_enc: 是否为加密操作
        enc_name: 是否加密文件名
        queue: 进程间通信队列，用于报告进度
        stop_event: 停止事件，用于中断任务
        pause_event: 暂停事件，用于暂停任务

    返回:
        元组 (文件路径, 成功标志, 消息, 输出路径)
    """
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
    """
    批量任务处理线程

    继承自 QThread，在后台线程中执行文件加密/解密任务。
    支持多进程并行处理、暂停/恢复、停止控制等功能。

    信号:
        sig_progress: 进度更新信号，参数为 (文本, 百分比)
        sig_log: 日志输出信号，参数为日志文本
        sig_finished: 任务完成信号，参数为结果字典

    属性:
        files: 待处理文件列表
        key: 加密密钥
        is_enc: 是否为加密操作
        enc_name: 是否加密文件名
        custom_out: 自定义输出目录
        keep_structure: 是否保留目录结构
        encrypt_dirname: 是否加密目录名
        use_ssd: 是否启用 SSD 加速
        ssd_dir: SSD 缓存目录
    """
    sig_progress = Signal(str, int)
    sig_log = Signal(str)
    sig_finished = Signal(dict)

    def __init__(self, files, key, is_encrypt, encrypt_filename=False,
                 custom_out_dir=None, keep_structure=False, encrypt_dirname=False,
                 use_ssd=False, ssd_dir=None):
        """
        初始化批量任务线程

        参数:
            files: 待处理文件路径列表
            key: 加密密钥字符串
            is_encrypt: True 表示加密，False 表示解密
            encrypt_filename: 是否加密文件名（仅加密时有效）
            custom_out_dir: 自定义输出目录，None 表示原地覆盖
            keep_structure: 是否保留原有目录结构
            encrypt_dirname: 是否加密目录名（需配合 keep_structure）
            use_ssd: 是否启用 SSD 加速（大文件场景推荐）
            ssd_dir: SSD 缓存目录路径
        """
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
        self.manager = None
        self.queue = None
        self.stop_event = None
        self.pause_event = None
        self.executor_class = ProcessPoolExecutor
        self.parallel_mode = "process"
        self._ipc_init_error = ""
        self._is_running = True
        self._init_ipc()

    def _init_ipc(self):
        """
        初始化进程间通信（IPC）机制

        尝试使用 multiprocessing.Manager 创建共享队列和事件，
        以支持多进程并行处理。如果失败（如 macOS 某些环境限制），
        则降级为线程池模式。

        多进程模式优势：充分利用多核 CPU，避免 GIL 限制
        线程池模式优势：兼容性更好，资源开销更小
        """
        try:
            self.manager = multiprocessing.Manager()
            self.queue = self.manager.Queue()
            self.stop_event = self.manager.Event()
            self.pause_event = self.manager.Event()
            self.executor_class = ProcessPoolExecutor
            self.parallel_mode = "process"
        except Exception as exc:
            self.manager = None
            self.queue = Queue()
            self.stop_event = threading.Event()
            self.pause_event = threading.Event()
            self.executor_class = ThreadPoolExecutor
            self.parallel_mode = "thread"
            self._ipc_init_error = str(exc)
        self.pause_event.set()

    def _shutdown_ipc(self):
        """清理 IPC 资源，关闭 multiprocessing.Manager"""
        if self.manager is not None:
            try:
                self.manager.shutdown()
            except (BrokenPipeError, EOFError, OSError):
                pass
            self.manager = None

    def pause(self):
        """暂停任务执行，工作线程将在当前文件完成后暂停"""
        self.pause_event.clear()

    def resume(self):
        """恢复被暂停的任务"""
        self.pause_event.set()

    def stop(self):
        self.stop_event.set()
        self._is_running = False

    def run(self):
        """
        线程主入口 - 执行批量文件处理

        执行流程:
        1. 准备阶段：计算密钥、扫描文件、计算总字节数
        2. SSD 加速：如启用，将文件先暂存到 SSD 再回写
        3. 并行处理：使用进程池/线程池并行处理文件
        4. 进度监控：定期从队列读取进度并更新 UI
        5. 结果收集：收集成功/失败结果并报告
        """
        try:
            key_bytes = hashlib.sha256(self.key.encode()).digest()
            results = {"success": [], "fail": []}
            valid_files = []
            total_bytes = 0
            self.processed_bytes_map = {}
            common_base = ""

            if self.parallel_mode == "thread" and self._ipc_init_error:
                self.sig_log.emit(f"⚠️ 多进程通信初始化失败，已降级为线程池模式: {self._ipc_init_error}")

            if self.keep_structure and len(self.files) > 0:
                try:
                    common_base = os.path.commonpath(self.files)
                    if os.path.isfile(common_base): common_base = os.path.dirname(common_base)
                except (ValueError, OSError):
                    pass

            self.sig_log.emit("--- 正在扫描任务队列 ---")
            for f in self.files:
                f_long = ensure_long_path(f)
                if os.path.exists(f_long):
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

            max_workers = min(os.cpu_count() or 1, len(valid_files))
            if self.use_ssd:
                max_workers = max(max_workers, 4)
            self.sig_log.emit(f"🚀 启动 {max_workers} 个{'进程' if self.parallel_mode == 'process' else '线程'}核心...")

            with self.executor_class(max_workers=max_workers) as executor:
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
                        except (ValueError, OSError):
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
                    except Empty:
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

                if not self._is_running:
                    executor.shutdown(wait=False, cancel_futures=True)

            if self.use_ssd and self._is_running and temp_stage_root:
                self.sig_log.emit("--- ⚡ SSD 高速回写 ---")
                try:
                    final_dest_root = self.custom_out
                    if not final_dest_root: final_dest_root = common_base if common_base else os.path.dirname(self.files[0])

                    final_dest_root = ensure_long_path(final_dest_root)
                    if not os.path.exists(final_dest_root): os.makedirs(final_dest_root, exist_ok=True)

                    items = os.listdir(temp_stage_root)
                    total_stage_bytes = 0
                    for item in items:
                        src_p = os.path.join(temp_stage_root, item)
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
        finally:
            self._shutdown_ipc()

    def _manual_move(self, src, dst, current_moved_total, total_stage_bytes):
        try:
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
                try:
                    if os.path.exists(src_long): shutil.copystat(src_long, dst_long)
                except OSError:
                    pass
                return current_moved_total
        except Exception as e:
            try:
                src_long = ensure_long_path(src)
                dst_long = ensure_long_path(dst)
                if os.path.exists(src_long) and not os.path.exists(dst_long):
                    shutil.move(src_long, dst_long)
                    return current_moved_total + os.path.getsize(dst_long)
            except OSError:
                pass
            return current_moved_total


# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Security Engine Enterprise")
        self.setFixedSize(1200, 850)

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
        self.use_new_system = False
        self.native_glass = NativeGlassController(self)

        # 创建主题选择器
        self.theme_selector = ThemeSelector(self)
        self.theme_selector.setup_themes(THEMES)
        self.theme_selector.theme_selected.connect(self.on_theme_selected)

        # 创建系统托盘
        self._init_tray()

        self._init_ui()
        self.apply_theme()

    def _init_ui(self):
        # 主容器
        main_widget = QWidget()
        main_widget.setObjectName("MainSurface")
        main_widget.setAttribute(Qt.WA_TranslucentBackground)
        self.main_surface = main_widget
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # === 1. 左侧导航栏 (毛玻璃侧边栏) ===
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(210)
        self.sidebar.setObjectName("Sidebar")

        v_sidebar = QVBoxLayout(self.sidebar)
        v_sidebar.setContentsMargins(16, 24, 16, 20)
        v_sidebar.setSpacing(8)

        # 标题
        lbl_title = QLabel("Encryption Studio")
        lbl_title.setObjectName("AppTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setFixedHeight(48)
        v_sidebar.addWidget(lbl_title)

        v_sidebar.addSpacing(24)

        # 导航按钮
        self.btn_nav_enc = AnimatedSidebarButton("加密", "lock", self)
        self.btn_nav_dec = AnimatedSidebarButton("解密", "unlock", self)
        self.btn_nav_key = AnimatedSidebarButton("密钥", "key", self)
        self.btn_nav_log = AnimatedSidebarButton("日志", "doc", self)

        self.btn_nav_enc.setChecked(True)

        # 按钮组逻辑
        self.btn_nav_enc.clicked.connect(lambda: self.switch_page(0))
        self.btn_nav_dec.clicked.connect(lambda: self.switch_page(1))
        self.btn_nav_key.clicked.connect(lambda: self.switch_page(2))
        self.btn_nav_log.clicked.connect(lambda: self.switch_page(3))

        self.sidebar_btns = [self.btn_nav_enc, self.btn_nav_dec, self.btn_nav_key, self.btn_nav_log]
        for btn in self.sidebar_btns:
            v_sidebar.addWidget(btn)

        v_sidebar.addStretch()

        self.btn_theme = ModernButton("主题", "normal")
        self.btn_theme.setMinimumHeight(44)
        self.btn_theme.clicked.connect(self.show_theme_menu)
        self.all_buttons.append(self.btn_theme)
        v_sidebar.addWidget(self.btn_theme)

        # 版本信息
        lbl_version = QLabel("v1.0 nexus")
        lbl_version.setAlignment(Qt.AlignCenter)
        lbl_version.setObjectName("VersionLabel")
        v_sidebar.addWidget(lbl_version)

        main_layout.addWidget(self.sidebar)

        # === 2. 右侧内容区 ===
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, 1)

        self._init_page_encrypt()
        self._init_page_decrypt()
        self._init_page_key_management()
        self._init_page_log()

    def _init_tray(self):
        """初始化系统托盘"""
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fileenc.ico")
        if os.path.exists(icon_path):
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        else:
            self.tray_icon = QSystemTrayIcon(self)

        tray_menu = QMenu()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        encrypt_action = QAction("加密文件", self)
        encrypt_action.triggered.connect(lambda: self.show_and_switch(0))
        tray_menu.addAction(encrypt_action)

        decrypt_action = QAction("解密文件", self)
        decrypt_action.triggered.connect(lambda: self.show_and_switch(1))
        tray_menu.addAction(decrypt_action)

        log_action = QAction("查看日志", self)
        log_action.triggered.connect(lambda: self.show_and_switch(2))
        tray_menu.addAction(log_action)

        tray_menu.addSeparator()

        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_window(self):
        """显示主窗口"""
        self.show()
        self.activateWindow()
        self.raise_()

    def show_and_switch(self, page_index):
        """显示窗口并切换到指定页面"""
        self.show_window()
        self.switch_page(page_index)

    def on_tray_activated(self, reason):
        """托盘图标被激活"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def quit_app(self):
        """完全退出程序"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "当前有任务正在运行，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            self.worker.stop()

        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """关闭窗口事件 - 最小化到托盘"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Encryption Studio",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.Information,
            2000
        )

    def showEvent(self, event):
        """窗口可见后再尝试挂载 macOS 原生玻璃层。"""
        super().showEvent(event)
        self.apply_theme()

    def switch_page(self, index):
        """切换页面"""
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.sidebar_btns):
            btn.setChecked(i == index)
            btn.update()

    def _create_common_layout(self, is_encrypt):
        page = QWidget()
        # 使用 Splitter 允许用户调整左右比例
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: transparent;
            }
        """)

        # === 左侧：文件列表 (毛玻璃卡片) ===
        left_container = QFrame()
        left_container.setObjectName("ContentPanel")
        v_left = QVBoxLayout(left_container)
        v_left.setContentsMargins(20, 20, 20, 20)
        v_left.setSpacing(14)
        v_left.setAlignment(Qt.AlignTop)

        # 系统状态提示
        h_status = QHBoxLayout()
        if is_encrypt:
            self.lbl_enc_system = QLabel("老系统")
            self.lbl_enc_system.setObjectName("SystemBadge")
            h_status.addWidget(self.lbl_enc_system)
        else:
            self.lbl_dec_system = QLabel("老系统")
            self.lbl_dec_system.setObjectName("SystemBadge")
            h_status.addWidget(self.lbl_dec_system)
        h_status.addStretch()
        v_left.addLayout(h_status)

        lbl_list = QLabel("待处理文件队列")
        lbl_list.setObjectName("SectionTitle")
        v_left.addWidget(lbl_list)

        file_list = DragDropListWidget()
        v_left.addWidget(file_list, 1)

        # 按钮栏
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_add = ModernButton("添加文件", "normal")
        btn_add.clicked.connect(lambda: self.action_add_file(is_encrypt))
        self.all_buttons.append(btn_add)

        btn_add_folder = ModernButton("添加目录", "normal")
        btn_add_folder.clicked.connect(lambda: self.action_add_folder(is_encrypt))
        self.all_buttons.append(btn_add_folder)

        btn_del = ModernButton("移除选中", "normal")
        btn_del.clicked.connect(lambda: self.action_remove_file(file_list, is_encrypt))
        self.all_buttons.append(btn_del)

        btn_clr = ModernButton("清空", "normal")
        btn_clr.clicked.connect(lambda: (file_list.clear(), self.reset_ui_state(is_encrypt)))
        self.all_buttons.append(btn_clr)

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_add_folder)
        btn_bar.addWidget(btn_del)
        btn_bar.addWidget(btn_clr)
        btn_bar.addStretch()

        v_left.addLayout(btn_bar)
        splitter.addWidget(left_container)

        # === 右侧：配置面板 (毛玻璃卡片) ===
        right_container = QFrame()
        right_container.setObjectName("ConfigPanel")
        right_container.setMinimumWidth(380)
        right_container.setMaximumWidth(500)

        v_right = QVBoxLayout(right_container)
        v_right.setContentsMargins(0, 0, 0, 0)
        v_right.setSpacing(0)

        # 标题区域 - 固定在顶部 (紧凑)
        title_area = QWidget()
        title_area.setObjectName("ConfigTitleArea")
        title_area.setFixedHeight(48)
        v_title = QVBoxLayout(title_area)
        v_title.setContentsMargins(16, 12, 16, 8)
        lbl_settings = QLabel("任务配置")
        lbl_settings.setObjectName("SectionTitle")
        v_title.addWidget(lbl_settings)
        v_right.addWidget(title_area)

        # === 可滚动配置区域 ===
        scroll_area = SmoothScrollArea()
        scroll_area.setObjectName("ConfigScrollArea")
        scroll_area.setMinimumHeight(200)

        # 滚动内容容器
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        v_scroll = QVBoxLayout(scroll_content)
        v_scroll.setContentsMargins(16, 0, 16, 12)
        v_scroll.setSpacing(10)  # 减小间距

        # 1. 安全设置 (紧凑 GroupBox)
        grp_sec = QGroupBox("安全凭证")
        grp_sec.setObjectName("GlassGroupBox")
        v_sec = QVBoxLayout(grp_sec)
        v_sec.setSpacing(8)
        v_sec.setContentsMargins(12, 18, 12, 12)

        # 老系统：密码输入
        self.old_sec_widget = QWidget() if is_encrypt else QWidget()
        v_old_sec = QVBoxLayout(self.old_sec_widget)
        v_old_sec.setContentsMargins(0, 0, 0, 0)
        txt_pwd = QLineEdit()
        txt_pwd.setEchoMode(QLineEdit.Password)
        txt_pwd.setPlaceholderText("输入密码...")
        txt_pwd.setFixedHeight(36)  # 减小高度
        v_old_sec.addWidget(txt_pwd)
        v_sec.addWidget(self.old_sec_widget)

        # 新系统：密钥选择
        self.new_sec_widget = QWidget() if is_encrypt else QWidget()
        v_new_sec = QVBoxLayout(self.new_sec_widget)
        v_new_sec.setContentsMargins(0, 0, 0, 0)
        v_new_sec.setSpacing(6)

        if is_encrypt:
            lbl_key = QLabel("选择公钥（用于加密）:")
            lbl_key.setObjectName("InputLabel")
            v_new_sec.addWidget(lbl_key)
            combo_key = DropDownComboBox()
            combo_key.setPlaceholderText("选择公钥...")
            combo_key.setFixedHeight(36)  # 减小高度
            v_new_sec.addWidget(combo_key)
        else:
            lbl_key = QLabel("选择私钥（用于解密）:")
            lbl_key.setObjectName("InputLabel")
            v_new_sec.addWidget(lbl_key)
            combo_key = DropDownComboBox()
            combo_key.setPlaceholderText("选择私钥...")
            combo_key.setFixedHeight(36)  # 减小高度
            v_new_sec.addWidget(combo_key)
            txt_key_pwd = QLineEdit()
            txt_key_pwd.setEchoMode(QLineEdit.Password)
            txt_key_pwd.setPlaceholderText("输入私钥密码...")
            txt_key_pwd.setFixedHeight(36)  # 减小高度
            v_new_sec.addWidget(txt_key_pwd)

        v_sec.addWidget(self.new_sec_widget)
        self.new_sec_widget.hide()
        v_scroll.addWidget(grp_sec)

        # 2. 输出设置 (紧凑)
        grp_io = QGroupBox("输出路径")
        grp_io.setObjectName("GlassGroupBox")
        v_io = QVBoxLayout(grp_io)
        v_io.setSpacing(8)
        v_io.setContentsMargins(12, 18, 12, 12)

        h_path = QHBoxLayout()
        h_path.setSpacing(8)
        txt_path = QLineEdit()
        txt_path.setPlaceholderText("默认：覆盖源文件")
        txt_path.setReadOnly(True)
        txt_path.setFixedHeight(36)  # 减小高度
        h_path.addWidget(txt_path, 1)

        btn_path = ModernButton("浏览", "normal")
        btn_path.setMinimumWidth(80)  # 自适应宽度，最小80px
        btn_path.setFixedHeight(36)
        btn_path.clicked.connect(lambda: self.action_select_dir(is_encrypt))
        self.all_buttons.append(btn_path)
        h_path.addWidget(btn_path)
        v_io.addLayout(h_path)

        # 保留目录结构
        chk_struct = CustomCheckBox("保留目录结构")
        chk_struct.setEnabled(False)
        v_io.addWidget(chk_struct)

        # 加密/解密文件名
        chk_dir_name_enc = None
        if is_encrypt:
            chk_dir_name_enc = CustomCheckBox("加密文件夹名")
            chk_dir_name_enc.setEnabled(False)
            v_io.addWidget(chk_dir_name_enc)

            def on_struct_toggled(state):
                is_checked = (state == 2)
                if chk_dir_name_enc:
                    chk_dir_name_enc.setEnabled(is_checked)
                    if not is_checked: chk_dir_name_enc.setChecked(False)

            chk_struct.stateChanged.connect(on_struct_toggled)
        else:
            chk_dir_name_enc = CustomCheckBox("解密文件夹名")
            chk_dir_name_enc.setEnabled(False)
            v_io.addWidget(chk_dir_name_enc)

            def on_struct_toggled_dec(state):
                is_checked = (state == 2)
                if chk_dir_name_enc:
                    chk_dir_name_enc.setEnabled(is_checked)
                    if not is_checked: chk_dir_name_enc.setChecked(False)

            chk_struct.stateChanged.connect(on_struct_toggled_dec)

        v_scroll.addWidget(grp_io)

        # 3. 高级选项 (紧凑)
        grp_adv = QGroupBox("高级策略")
        grp_adv.setObjectName("GlassGroupBox")
        v_adv = QVBoxLayout(grp_adv)
        v_adv.setSpacing(8)
        v_adv.setContentsMargins(12, 18, 12, 12)

        h_ssd = QHBoxLayout()
        h_ssd.setSpacing(8)
        txt_ssd = QLineEdit()
        txt_ssd.setPlaceholderText("选择 SSD 缓存路径...")
        txt_ssd.setReadOnly(True)
        txt_ssd.setFixedHeight(36)  # 减小高度
        h_ssd.addWidget(txt_ssd, 1)

        btn_ssd = ModernButton("选择", "normal")
        btn_ssd.setMinimumWidth(80)  # 自适应宽度最小80px
        btn_ssd.setFixedHeight(36)
        btn_ssd.clicked.connect(lambda: self.action_select_ssd(is_encrypt))
        self.all_buttons.append(btn_ssd)
        h_ssd.addWidget(btn_ssd)
        v_adv.addLayout(h_ssd)

        chk_ssd = CustomCheckBox("启用 SSD 加速")
        chk_ssd.setEnabled(False)
        v_adv.addWidget(chk_ssd)

        chk_name = None
        chk_del = None
        if is_encrypt:
            chk_name = CustomCheckBox("混淆文件名")
            chk_name.setChecked(True)
            v_adv.addWidget(chk_name)
            chk_del = CustomCheckBox("完成后粉碎源文件")
            v_adv.addWidget(chk_del)
        else:
            chk_del = CustomCheckBox("解密后移除加密包")
            v_adv.addWidget(chk_del)

        v_scroll.addWidget(grp_adv)
        v_scroll.addStretch()

        scroll_area.setWidget(scroll_content)
        scroll_area.update_theme(self.theme_data)
        v_right.addWidget(scroll_area, 1)

        # === 底部状态与控制区 - 固定在底部 (紧凑) ===
        bottom_area = QWidget()
        bottom_area.setObjectName("BottomArea")
        bottom_area.setFixedHeight(110)
        v_bottom = QVBoxLayout(bottom_area)
        v_bottom.setContentsMargins(16, 10, 16, 14)
        v_bottom.setSpacing(8)

        # 状态显示区域 (毛玻璃卡片)
        status_container = QFrame()
        status_container.setObjectName("StatusContainer")
        v_status = QVBoxLayout(status_container)
        v_status.setContentsMargins(12, 10, 12, 10)
        v_status.setSpacing(10)  # 增加标签和进度条之间的间距

        lbl_status = QLabel("就绪")
        lbl_status.setAlignment(Qt.AlignCenter)
        lbl_status.setObjectName("StatusLabel")
        lbl_status.setFixedHeight(18)  # 确保标签高度足够显示文字
        lbl_status.setFont(QFont(get_system_font_family(), 11, QFont.DemiBold))
        v_status.addWidget(lbl_status)

        pbar = GlassProgressBar()  # 使用新的玻璃质感进度条
        pbar.setValue(0)
        v_status.addWidget(pbar)

        v_bottom.addWidget(status_container)

        # 操作按钮区 (紧凑)
        stack = QStackedWidget()
        stack.setFixedHeight(40)  # 减小高度

        # Start
        w_start = QWidget()
        l_start = QHBoxLayout(w_start)
        l_start.setContentsMargins(0, 0, 0, 0)
        btn_run = ModernButton(f"开始{'加密' if is_encrypt else '解密'}", "primary")
        btn_run.setFixedHeight(40)  # 减小高度
        btn_run.clicked.connect(self.run_encrypt if is_encrypt else self.run_decrypt)
        self.all_buttons.append(btn_run)
        l_start.addWidget(btn_run)
        stack.addWidget(w_start)

        # Running
        w_ctrl = QWidget()
        l_ctrl = QHBoxLayout(w_ctrl)
        l_ctrl.setContentsMargins(0, 0, 0, 0)
        l_ctrl.setSpacing(8)
        btn_pause = ModernButton("挂起", "normal")
        btn_pause.setFixedHeight(40)
        btn_pause.clicked.connect(self.action_toggle_pause)
        self.all_buttons.append(btn_pause)
        btn_stop = ModernButton("终止", "danger")
        btn_stop.setFixedHeight(40)
        btn_stop.clicked.connect(self.action_stop_task)
        self.all_buttons.append(btn_stop)
        l_ctrl.addWidget(btn_pause)
        l_ctrl.addWidget(btn_stop)
        stack.addWidget(w_ctrl)

        # Finish
        w_res = QWidget()
        l_res = QHBoxLayout(w_res)
        l_res.setContentsMargins(0, 0, 0, 0)
        l_res.setSpacing(8)
        btn_open = ModernButton("打开目录", "normal")
        btn_open.setFixedHeight(40)
        btn_open.clicked.connect(self.action_open_folder)
        self.all_buttons.append(btn_open)
        btn_back = ModernButton("返回", "normal")
        btn_back.setFixedHeight(40)
        btn_back.clicked.connect(lambda: self.reset_ui_state(is_encrypt))
        self.all_buttons.append(btn_back)
        l_res.addWidget(btn_open)
        l_res.addWidget(btn_back)
        stack.addWidget(w_res)

        v_bottom.addWidget(stack)
        v_right.addWidget(bottom_area)

        splitter.addWidget(right_container)

        # 设置 Splitter 比例
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        # 包装到 Layout
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        refs = {
            "list": file_list, "pwd": txt_pwd, "path": txt_path,
            "chk_name": chk_name, "chk_del": chk_del,
            "chk_struct": chk_struct, "chk_dir_name_enc": chk_dir_name_enc,
            "chk_ssd": chk_ssd, "txt_ssd": txt_ssd,
            "status": lbl_status, "pbar": pbar, "stack": stack,
            "btn_pause": btn_pause,
            "old_sec_widget": self.old_sec_widget,
            "new_sec_widget": self.new_sec_widget,
            "combo_key": combo_key,
            "txt_key_pwd": txt_key_pwd if not is_encrypt else None,
            "scroll_area": scroll_area
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

    def _init_page_key_management(self):
        import json
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("ContentPanel")
        v = QVBoxLayout(container)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(20)

        lbl = QLabel("密钥管理中心")
        lbl.setObjectName("SectionTitle")
        v.addWidget(lbl)

        # 系统切换卡片 (紧凑布局)
        switch_card = QFrame()
        switch_card.setObjectName("SwitchCard")
        switch_card.setFixedHeight(64)
        h_switch = QHBoxLayout(switch_card)
        h_switch.setContentsMargins(16, 12, 16, 12)
        h_switch.setSpacing(12)

        icon_lbl = QLabel("KEY")
        icon_lbl.setObjectName("SystemGlyph")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(42, 34)
        h_switch.addWidget(icon_lbl)

        v_status = QVBoxLayout()
        v_status.setSpacing(2)
        self.lbl_system_status = QLabel("老加密系统")
        self.lbl_system_status.setObjectName("SystemStatusTitle")
        self.lbl_system_desc = QLabel("对称加密 (AES-256)")
        self.lbl_system_desc.setObjectName("SystemStatusDesc")
        v_status.addWidget(self.lbl_system_status)
        v_status.addWidget(self.lbl_system_desc)
        h_switch.addLayout(v_status)
        h_switch.addStretch()

        self.btn_switch_system = SystemSwitchButton("切换到新系统 →")
        self.btn_switch_system.setFixedSize(160, 32)  # 加宽以完整显示文字
        self.btn_switch_system.clicked.connect(self.action_switch_system)
        h_switch.addWidget(self.btn_switch_system)
        v.addWidget(switch_card)

        # 密钥列表标题
        lbl_list = QLabel("密钥列表")
        lbl_list.setObjectName("SubSectionTitle")
        v.addWidget(lbl_list)

        self.key_list = QListWidget()
        self.key_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.key_list.setMinimumHeight(280)  # 增加密钥列表高度
        v.addWidget(self.key_list, 1)  # 添加拉伸因子，让列表占据更多空间

        # 老系统提示
        self.old_system_widget = QWidget()
        v_old = QVBoxLayout(self.old_system_widget)
        v_old.setContentsMargins(0, 0, 0, 0)
        lbl_old_tip = QLabel("老系统使用对称加密，加密时直接输入密码即可，无需预先生成密钥")
        lbl_old_tip.setObjectName("InfoTip")
        lbl_old_tip.setWordWrap(True)
        v_old.addWidget(lbl_old_tip)
        v.addWidget(self.old_system_widget)

        # 新系统输入框 (紧凑布局)
        self.new_system_widget = QWidget()
        v_new = QVBoxLayout(self.new_system_widget)
        v_new.setContentsMargins(0, 0, 0, 0)
        v_new.setSpacing(8)

        lbl_new_tip = QLabel("生成新密钥对")
        lbl_new_tip.setObjectName("SubSectionTitle")
        v_new.addWidget(lbl_new_tip)

        h_new = QHBoxLayout()
        h_new.setSpacing(10)
        self.new_key_name_input = QLineEdit()
        self.new_key_name_input.setPlaceholderText("密钥对名称 (例如: my_key)")
        self.new_key_name_input.setFixedHeight(36)  # 减小高度
        self.new_key_password_input = QLineEdit()
        self.new_key_password_input.setPlaceholderText("保护密码")
        self.new_key_password_input.setEchoMode(QLineEdit.Password)
        self.new_key_password_input.setFixedHeight(36)  # 减小高度
        h_new.addWidget(self.new_key_name_input, 2)
        h_new.addWidget(self.new_key_password_input, 1)
        v_new.addLayout(h_new)
        v.addWidget(self.new_system_widget)
        self.new_system_widget.hide()

        # 按钮栏 (紧凑布局)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_gen_new = ModernButton("生成密钥对", "primary")
        self.btn_gen_new.setFixedHeight(34)  # 减小高度
        self.btn_gen_new.clicked.connect(self.action_generate_keypair)
        self.all_buttons.append(self.btn_gen_new)
        self.btn_gen_new.hide()

        self.btn_import_new = ModernButton("导入", "normal")
        self.btn_import_new.setFixedHeight(34)  # 减小高度
        self.btn_import_new.clicked.connect(self.action_import_keypair)
        self.all_buttons.append(self.btn_import_new)
        self.btn_import_new.hide()

        btn_delete = ModernButton("删除", "danger")
        btn_delete.setFixedHeight(34)  # 减小高度
        btn_delete.clicked.connect(self.action_delete_key)
        self.all_buttons.append(btn_delete)

        btn_refresh = ModernButton("刷新", "normal")
        btn_refresh.setFixedHeight(34)  # 减小高度
        btn_refresh.clicked.connect(self.action_refresh_keys)
        self.all_buttons.append(btn_refresh)

        btn_bar.addWidget(self.btn_gen_new)
        btn_bar.addWidget(self.btn_import_new)
        btn_bar.addWidget(btn_delete)
        btn_bar.addWidget(btn_refresh)
        btn_bar.addStretch()

        v.addLayout(btn_bar)
        layout.addWidget(container)
        self.content_stack.addWidget(page)
        self.action_refresh_keys()

    def _init_page_log(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("ContentPanel")
        v = QVBoxLayout(container)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        lbl = QLabel("系统运行日志")
        lbl.setObjectName("SectionTitle")
        v.addWidget(lbl)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setObjectName("LogTextEdit")
        v.addWidget(self.txt_log)

        layout.addWidget(container)
        self.content_stack.addWidget(page)

    def show_theme_menu(self):
        """显示主题选择菜单"""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)

        t = self.theme_data
        menu.setStyleSheet(f"""
            QMenu {{
                background: {t['panel_elevated']};
                color: {t['fg']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 10px 24px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background: {t['accent']};
                color: white;
            }}
        """)

        for theme_name in self.theme_names:
            action = menu.addAction(theme_name)
            action.triggered.connect(lambda checked=False, name=theme_name: self.on_theme_selected(name))

        menu.exec(self.btn_theme.mapToGlobal(QPoint(0, self.btn_theme.height())))

    def show_theme_selector(self):
        """显示主题选择器"""
        btn_pos = self.btn_theme.mapToGlobal(QPoint(0, 0))
        popup_x = btn_pos.x() + self.btn_theme.width() + 10
        popup_y = btn_pos.y() - (self.theme_selector.height() - self.btn_theme.height()) // 2
        self.theme_selector.show_at(QPoint(popup_x, popup_y))

    def on_theme_selected(self, theme_name):
        """主题被选中"""
        self.current_theme_idx = self.theme_names.index(theme_name)
        self.apply_theme()

    def cycle_theme(self):
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.theme_names)
        self.apply_theme()

    def apply_theme(self):
        """应用 mac-first Liquid Glass 主题。"""
        theme_name = self.theme_names[self.current_theme_idx]
        t = THEMES[theme_name]
        self.theme_data = t
        self.btn_theme.setText(f"{theme_name}")
        native_glass_enabled = self.native_glass.apply(t)
        window_bg = "transparent" if native_glass_enabled else t["bg"]

        for widget in self.findChildren(QLineEdit):
            widget.setTextMargins(10, 0, 10, 0)

        qss = f"""
        QMainWindow {{
            background: {window_bg};
        }}
        QWidget#MainSurface {{
            background: transparent;
        }}
        QWidget {{
            color: {t['fg']};
            font-family: {get_system_font_qss()};
            font-size: {t['body_size']};
            font-weight: {t['body_weight']};
        }}

        QFrame#Sidebar {{
            background: {t['sidebar']};
            border: 1px solid {t['glass_border']};
            border-bottom: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_lg']};
        }}
        QLabel#AppTitle {{
            color: {t['fg']};
            font-size: 17px;
            font-weight: 700;
        }}
        QLabel#VersionLabel {{
            color: {t['fg_tertiary']};
            font-size: 11px;
            font-weight: 500;
        }}

        QFrame#ContentPanel {{
            background: {t['panel']};
            border: 1px solid {t['glass_border']};
            border-bottom: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_lg']};
        }}

        QFrame#ConfigPanel {{
            background: {t['config_panel']};
            border: 1px solid {t['config_panel_border']};
            border-bottom: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_lg']};
        }}
        QWidget#ConfigTitleArea {{
            background: transparent;
            border-bottom: 1px solid {t['separator']};
        }}
        QWidget#BottomArea {{
            background: transparent;
            border-top: 1px solid {t['separator']};
        }}

        QLabel#SectionTitle {{
            color: {t['fg']};
            font-size: {t['section_title_size']};
            font-weight: {t['section_title_weight']};
        }}
        QLabel#SubSectionTitle {{
            color: {t['fg_secondary']};
            font-size: 12px;
            font-weight: 600;
        }}
        QLabel#InputLabel {{
            color: {t['fg_secondary']};
            font-size: 12px;
            font-weight: 500;
        }}
        QLabel#SystemBadge {{
            color: {t['accent']};
            font-weight: 600;
            font-size: 11px;
            background: {t['accent_light']};
            padding: 4px 11px;
            border-radius: {t['radius_xs']};
            border: 1px solid {t['sidebar_active_border']};
        }}

        QPushButton {{
            background: {t['panel']};
            border: 1px solid {t['border']};
            border-bottom: 1px solid {t['border_dark']};
            border-radius: {t['radius_sm']};
            color: {t['fg']};
            padding: 8px 18px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {t['sidebar_hover']};
            border-color: {t['glass_border']};
        }}
        QPushButton:pressed {{
            background: {t['card_bg']};
        }}

        QLineEdit, QTextEdit, QComboBox {{
            background: {t['input_bg']};
            border: 1px solid {t['input_border']};
            border-bottom: 1px solid {t['border_dark']};
            border-radius: {t['radius_md']};
            color: {t['fg']};
            padding: 0 14px;
            font-size: 13px;
            selection-background-color: {t['accent']};
            selection-color: white;
        }}
        QLineEdit:focus, QComboBox:focus {{
            background: {t['input_bg_hover']};
            border: 1.5px solid {t['border_focus']};
        }}
        QLineEdit:hover, QComboBox:hover {{
            background: {t['input_bg_hover']};
        }}
        QComboBox {{
            padding-right: 36px;
            min-height: 40px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 36px;
        }}
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
            margin-right: 12px;
        }}
        QComboBox QAbstractItemView {{
            background: {t['panel_elevated']};
            border: 1px solid {t['border']};
            border-radius: {t['radius_sm']};
            selection-background-color: {t['accent']};
            selection-color: white;
            padding: 6px;
            outline: none;
            margin-top: 4px;
        }}

        QGroupBox#GlassGroupBox {{
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-bottom: 1px solid {t['border_dark']};
            border-radius: {t['radius_md']};
            margin-top: 20px;
            padding: 18px 14px 14px 14px;
            font-weight: 600;
            font-size: 12px;
            color: {t['fg']};
        }}
        QGroupBox#GlassGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 16px;
            padding: 0 8px;
            color: {t['fg_secondary']};
        }}

        QFrame#ConfigPanelCard {{
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_md']};
        }}
        QWidget#CardTitleBar {{
            background: transparent;
            border-bottom: 1px solid {t['separator']};
        }}
        QLabel#CardTitleLabel {{
            color: {t['fg_secondary']};
            font-size: 12px;
            font-weight: 600;
        }}
        QWidget#CardContent {{
            background: transparent;
        }}

        QFrame#StatusContainer {{
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-bottom: 1px solid {t['border_dark']};
            border-radius: {t['radius_md']};
        }}
        QLabel#StatusLabel {{
            color: {t['fg_secondary']};
        }}

        QListWidget {{
            background: {t['list_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-bottom: 1px solid {t['border_dark']};
            border-radius: {t['radius_md']};
            padding: 6px;
            outline: none;
        }}
        QListWidget::item {{
            border-radius: 8px;
            padding: 10px 14px;
            margin: 3px 4px;
            color: {t['fg']};
        }}
        QListWidget::item:selected {{
            background: {t['list_item_selected']};
            color: {t['accent']};
        }}
        QListWidget::item:hover:!selected {{
            background: {t['list_item_hover']};
        }}

        QProgressBar {{
            background: {t['card_bg']};
            border: none;
            border-radius: 3px;
            text-align: center;
            height: 6px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {t['accent']}, stop:1 {t['accent_hover']});
            border-radius: 3px;
        }}

        QCheckBox {{
            spacing: 10px;
            color: {t['fg']};
            font-size: 13px;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 6px;
            border: 1.5px solid {t['input_border']};
            background: {t['input_bg']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {t['accent']};
        }}
        QCheckBox::indicator:checked {{
            background: {t['accent']};
            border-color: {t['accent']};
        }}

        QSplitter::handle {{
            background: transparent;
        }}

        QFrame#SwitchCard {{
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-bottom: 1px solid {t['border_dark']};
            border-radius: {t['radius_md']};
        }}
        QLabel#SystemGlyph {{
            color: {t['accent']};
            font-size: 12px;
            font-weight: 800;
            background: {t['accent_light']};
            border: 1px solid {t['sidebar_active_border']};
            border-radius: {t['radius_sm']};
            padding: 6px 8px;
        }}
        QLabel#SystemStatusTitle {{
            font-weight: 600;
            font-size: 14px;
            color: {t['accent']};
        }}
        QLabel#SystemStatusDesc {{
            color: {t['fg_secondary']};
            font-size: 12px;
        }}
        QLabel#InfoTip {{
            color: {t['fg_secondary']};
            padding: 14px 16px;
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_sm']};
            font-size: 12px;
        }}

        QTextEdit#LogTextEdit {{
            background: {t['list_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-bottom: 1px solid {t['border_dark']};
            border-radius: {t['radius_md']};
            padding: 12px;
            font-family: {get_monospace_font_qss()};
            font-size: 12px;
        }}
        """
        self.setStyleSheet(qss)
        for btn in self.all_buttons:
            btn.update_theme(t)

        for btn in self.sidebar_btns:
            btn.update()

        self.ui_enc["list"].update_theme(t)
        self.ui_dec["list"].update_theme(t)

        if "scroll_area" in self.ui_enc:
            self.ui_enc["scroll_area"].update_theme(t)
        if "scroll_area" in self.ui_dec:
            self.ui_dec["scroll_area"].update_theme(t)

    # ================= 逻辑控制 =================
    def check_constraints(self):
        # 1. 输出路径 -> 保留目录结构
        enc_path = self.custom_enc_path
        if not enc_path:
            self.ui_enc["chk_struct"].setChecked(False)
            self.ui_enc["chk_struct"].setEnabled(False)
        else:
            self.ui_enc["chk_struct"].setEnabled(True)

        dec_path = self.custom_dec_path
        if not dec_path:
            self.ui_dec["chk_struct"].setChecked(False)
            self.ui_dec["chk_struct"].setEnabled(False)
        else:
            self.ui_dec["chk_struct"].setEnabled(True)

        # 2. SSD 路径 -> 启用 SSD 加速
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
            added_count = 0
            for f in files:
                if f not in existing:
                    ui["list"].addItem(f)
                    added_count += 1
                    sys_logger.log(f"添加文件: {f}")
            self.append_log(f"添加了 {added_count} 个文件到队列")
            self.check_constraints()

    def action_add_folder(self, is_encrypt):
        """新增：添加目录功能，递归读取目录下所有文件"""
        self.reset_ui_state(is_encrypt)
        ui = self.ui_enc if is_encrypt else self.ui_dec
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            existing = set([ui["list"].item(i).text() for i in range(ui["list"].count())])
            added = 0
            sys_logger.log(f"开始扫描文件夹: {d}")
            for root, _, files in os.walk(d):
                for file in files:
                    full_path = os.path.normpath(os.path.join(root, file))
                    if full_path not in existing:
                        ui["list"].addItem(full_path)
                        existing.add(full_path)
                        added += 1
            self.append_log(f"从文件夹添加了 {added} 个文件")
            sys_logger.log(f"文件夹扫描完成，共添加 {added} 个文件")
            if added:
                self.check_constraints()

    def action_remove_file(self, lst, is_encrypt):
        self.reset_ui_state(is_encrypt)
        removed_count = 0
        for item in lst.selectedItems():
            file_path = item.text()
            lst.takeItem(lst.row(item))
            sys_logger.log(f"移除文件: {file_path}")
            removed_count += 1
        if removed_count > 0:
            self.append_log(f"移除了 {removed_count} 个文件")
        self.check_constraints()

    def action_select_dir(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            if is_encrypt:
                self.custom_enc_path = d
                self.ui_enc["path"].setText(d)
                sys_logger.log(f"[加密] 选择输出目录: {d}")
                self.append_log(f"输出目录已设置: {d}")
            else:
                self.custom_dec_path = d
                self.ui_dec["path"].setText(d)
                sys_logger.log(f"[解密] 选择输出目录: {d}")
                self.append_log(f"输出目录已设置: {d}")
        self.check_constraints()

    def action_select_ssd(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择 SSD 缓存目录")
        if d:
            self.custom_ssd_path = d
            self.ui_enc["txt_ssd"].setText(d)
            self.ui_dec["txt_ssd"].setText(d)
            sys_logger.log(f"选择 SSD 缓存目录: {d}")
            self.append_log(f"SSD 缓存已设置: {d}")
        self.check_constraints()

    def reset_ui_state(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        ui["stack"].setCurrentIndex(0)
        ui["pbar"].reset()  # 重置进度条并停止动画
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

        files = [ui["list"].item(i).text() for i in range(count)]
        path = self.custom_enc_path if is_encrypt else self.custom_dec_path

        if self.use_new_system:
            key_name = ui["combo_key"].currentText()
            if not key_name:
                return QMessageBox.warning(self, "提示", "请选择密钥对")

            keys_dir = DIRS["KEYS"]
            if is_encrypt:
                key_path = os.path.join(keys_dir, f"{key_name}_public.pem")
                key_pwd = None
            else:
                key_path = os.path.join(keys_dir, f"{key_name}_private.pem")
                key_pwd = ui["txt_key_pwd"].text() if ui["txt_key_pwd"] else None
                if not key_pwd:
                    return QMessageBox.warning(self, "提示", "请输入私钥密码")

            if not os.path.exists(key_path):
                return QMessageBox.warning(self, "错误", f"密钥文件不存在: {key_path}")

            sys_logger.log(f"[新系统] 使用密钥: {key_name}")
            self._start_new_system_process(is_encrypt, files, path, key_path, key_pwd, ui)
        else:
            pwd = ui["pwd"].text()
            if not pwd:
                return QMessageBox.warning(self, "安全提示", "必须输入密码。")
            self._start_old_system_process(is_encrypt, files, path, pwd, ui)

    def _start_old_system_process(self, is_encrypt, files, path, pwd, ui):
        """老系统加密/解密"""
        keep_struct = ui["chk_struct"].isChecked()
        enc_dirname = False

        if is_encrypt and ui.get("chk_dir_name_enc"):
            enc_dirname = ui["chk_dir_name_enc"].isEnabled() and ui["chk_dir_name_enc"].isChecked()
        elif not is_encrypt and ui.get("chk_dir_name_enc"):
            enc_dirname = ui["chk_dir_name_enc"].isEnabled() and ui["chk_dir_name_enc"].isChecked()

        use_ssd = ui["chk_ssd"].isChecked()
        ssd_path = self.custom_ssd_path if use_ssd else None

        if use_ssd and (not ssd_path or not os.path.exists(ssd_path)):
            return QMessageBox.warning(self, "参数缺失", "请选择有效的 SSD 缓存目录。")

        task_type = "加密" if is_encrypt else "解密"
        sys_logger.log(f"========== [老系统] 开始{task_type}任务 ==========")
        sys_logger.log(f"文件数量: {len(files)}")
        sys_logger.log(f"输出目录: {path if path else '原地覆盖'}")

        ui["list"].setEnabled(False)
        ui["pwd"].setEnabled(False)
        ui["stack"].setCurrentIndex(1)
        ui["pbar"].setValue(0)
        ui["pbar"].start_shimmer()  # 启动流光动画
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

    def _start_new_system_process(self, is_encrypt, files, path, key_path, key_pwd, ui):
        """新系统加密/解密"""
        from core.rsa_cipher import RSAFileCipher

        task_type = "加密" if is_encrypt else "解密"
        sys_logger.log(f"========== [新系统] 开始{task_type}任务 ==========")
        sys_logger.log(f"文件数量: {len(files)}")
        sys_logger.log(f"密钥: {os.path.basename(key_path)}")

        ui["list"].setEnabled(False)
        ui["stack"].setCurrentIndex(1)
        ui["pbar"].setValue(0)
        ui["pbar"].start_shimmer()  # 启动流光动画
        ui["status"].setText("初始化引擎...")

        results = {"success": [], "fail": []}
        total = len(files)

        for idx, f in enumerate(files):
            try:
                fname = os.path.basename(f)
                out_dir = path if path else os.path.dirname(f)
                if is_encrypt:
                    if ui.get("chk_name") and ui["chk_name"].isChecked():
                        import uuid
                        random_name = str(uuid.uuid4().hex)[:12] + ".enc"
                        out_path = os.path.join(out_dir, random_name)
                    else:
                        out_path = os.path.join(out_dir, fname + ".enc")
                    success, msg = RSAFileCipher.encrypt_file(f, out_path, key_path)
                else:
                    out_path = os.path.join(out_dir, fname.replace(".enc", ""))
                    result = RSAFileCipher.decrypt_file(f, out_path, key_path, key_pwd)
                    if len(result) == 3:
                        success, msg, actual_out_path = result
                        if success:
                            out_path = actual_out_path
                    else:
                        success, msg = result[0], result[1]

                if success:
                    results["success"].append((f, out_path))
                    sys_logger.log(f"✅ {fname}")
                else:
                    results["fail"].append((f, msg))
                    sys_logger.log(f"❌ {fname}: {msg}")
            except Exception as e:
                results["fail"].append((f, str(e)))
                sys_logger.log(f"❌ {fname}: {e}")

            progress = int((idx + 1) / total * 100)
            ui["pbar"].setValue(progress)
            ui["status"].setText(f"处理中... {idx + 1}/{total}")
            QApplication.processEvents()

        self.on_finished(results, is_encrypt)

    def update_progress(self, text, val):
        if not self.worker: return
        is_enc_task = self.worker.is_enc
        ui = self.ui_enc if is_enc_task else self.ui_dec
        ui["status"].setText(text)
        ui["pbar"].setValue(val)

    def append_log(self, text):
        t = datetime.now().strftime("%H:%M:%S")
        color = self.theme_data['fg_secondary']
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
        ui["pbar"].stop_shimmer()  # 停止流光动画
        ui["list"].setEnabled(True)
        ui["pwd"].setEnabled(True)
        ui["list"].clear()

        task_type = "加密" if is_encrypt else "解密"

        if results["success"]:
            self.last_out_dir = os.path.dirname(results["success"][0][1])
            sys_logger.log(f"========== {task_type}成功文件列表 ==========")
            for src, dst in results["success"]:
                sys_logger.log(f"源文件: {src}")
                sys_logger.log(f"目标文件: {dst}")
                sys_logger.log("---")

        if results["fail"]:
            sys_logger.log(f"========== {task_type}失败文件列表 ==========")
            for src, err in results["fail"]:
                sys_logger.log(f"文件: {src}")
                sys_logger.log(f"错误: {err}")
                sys_logger.log("---")

        chk_del = ui["chk_del"]
        if chk_del.isChecked():
            self.append_log("执行安全删除...")
            sys_logger.log("开始删除源文件...")
            for src, _ in results["success"]:
                try:
                    os.remove(src)
                    sys_logger.log(f"已删除: {src}")
                except Exception as e:
                    sys_logger.log(f"删除失败: {src}, 错误: {e}")

        succ = len(results["success"])
        fail = len(results["fail"])
        sys_logger.log(f"========== {task_type}任务完成 ==========")
        sys_logger.log(f"成功: {succ} 个, 失败: {fail} 个")

        if fail == 0:
            QMessageBox.information(self, "完成", f"成功处理 {succ} 个文件")
        else:
            QMessageBox.warning(self, "完成", f"成功: {succ}, 失败: {fail}")

    def action_open_folder(self):
        if self.last_out_dir and os.path.exists(self.last_out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out_dir))
        else:
            QMessageBox.information(self, "提示", "目录不存在")

    def action_refresh_keys(self):
        self.key_list.clear()
        if self.use_new_system:
            keys_dir = DIRS["KEYS"]
            key_pairs = {}

            for f in os.listdir(keys_dir):
                if f.endswith('_private.pem'):
                    key_name = f.replace('_private.pem', '')
                    if key_name not in key_pairs:
                        key_pairs[key_name] = {'private': None, 'public': None}
                    key_pairs[key_name]['private'] = f
                elif f.endswith('_public.pem'):
                    key_name = f.replace('_public.pem', '')
                    if key_name not in key_pairs:
                        key_pairs[key_name] = {'private': None, 'public': None}
                    key_pairs[key_name]['public'] = f

            for key_name, files in sorted(key_pairs.items()):
                self.key_list.addItem(f"密钥对: {key_name}")
                if files['public']:
                    self.key_list.addItem(f"  公钥: {files['public']}")
                if files['private']:
                    self.key_list.addItem(f"  私钥: {files['private']}")

            sys_logger.log(f"[新系统] 刷新密钥列表，共 {len(key_pairs)} 个密钥对")
        else:
            self.key_list.addItem("老系统无需管理密钥，加密时直接输入密码即可")
            sys_logger.log(f"[老系统] 无需密钥管理")

    def action_switch_system(self):
        self.use_new_system = not self.use_new_system
        self.btn_switch_system.set_new_system(self.use_new_system)  # 使用新方法设置状态
        if self.use_new_system:
            self.lbl_system_status.setText("新加密系统")
            self.lbl_system_desc.setText("非对称加密 (RSA-2048)")
            self.old_system_widget.hide()
            self.new_system_widget.show()
            self.btn_gen_new.show()
            self.btn_import_new.show()
            self.lbl_enc_system.setText("新系统")
            if hasattr(self, 'lbl_dec_system'):
                self.lbl_dec_system.setText("新系统")
            self.ui_enc["old_sec_widget"].hide()
            self.ui_enc["new_sec_widget"].show()
            self.ui_dec["old_sec_widget"].hide()
            self.ui_dec["new_sec_widget"].show()
            self.refresh_key_combos()
        else:
            self.lbl_system_status.setText("老加密系统")
            self.lbl_system_desc.setText("对称加密 (AES-256)")
            self.old_system_widget.show()
            self.new_system_widget.hide()
            self.btn_gen_new.hide()
            self.btn_import_new.hide()
            self.lbl_enc_system.setText("老系统")
            if hasattr(self, 'lbl_dec_system'):
                self.lbl_dec_system.setText("老系统")
            self.ui_enc["old_sec_widget"].show()
            self.ui_enc["new_sec_widget"].hide()
            self.ui_dec["old_sec_widget"].show()
            self.ui_dec["new_sec_widget"].hide()
        self.action_refresh_keys()
        sys_logger.log(f"切换到{'新' if self.use_new_system else '老'}加密系统")
        self.append_log(f"已切换到{'新' if self.use_new_system else '老'}加密系统")

    def refresh_key_combos(self):
        """刷新加密/解密界面的密钥下拉列表"""
        keys_dir = DIRS["KEYS"]
        key_pairs = []
        for f in os.listdir(keys_dir):
            if f.endswith('_private.pem'):
                key_pairs.append(f.replace('_private.pem', ''))

        self.ui_enc["combo_key"].clear()
        self.ui_dec["combo_key"].clear()
        for kp in key_pairs:
            self.ui_enc["combo_key"].addItem(kp)
            self.ui_dec["combo_key"].addItem(kp)

    def action_generate_keypair(self):
        from core.rsa_cipher import RSAKeyManager
        name = self.new_key_name_input.text().strip()
        pwd = self.new_key_password_input.text().strip()
        if not name or not pwd:
            return QMessageBox.warning(self, "提示", "请输入密钥对名称和保护密码")

        try:
            private_pem, public_pem = RSAKeyManager.generate_key_pair(pwd, name)
            keys_dir = DIRS["KEYS"]

            private_path = os.path.join(keys_dir, f"{name}_private.pem")
            public_path = os.path.join(keys_dir, f"{name}_public.pem")

            with open(private_path, 'wb') as f:
                f.write(private_pem)
            with open(public_path, 'wb') as f:
                f.write(public_pem)

            sys_logger.log(f"生成密钥对: {name}")
            self.append_log(f"生成密钥对: {name}")
            self.new_key_name_input.clear()
            self.new_key_password_input.clear()
            self.action_refresh_keys()

            QMessageBox.information(self, "成功",
                f"密钥对已生成！\n\n私钥: {private_path}\n公钥: {public_path}\n\n⚠️ 请妥善保管私钥和密码！")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"生成失败: {e}")

    def action_import_keypair(self):
        """导入密钥对（公钥+私钥）"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit

        dialog = QDialog(self)
        dialog.setWindowTitle("导入密钥对")
        dialog.setFixedSize(500, 200)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl_pub = QLabel("公钥文件:")
        lbl_pub.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_pub)

        h_pub = QHBoxLayout()
        h_pub.setStretch(0, 1)  # 输入框占满剩余空间
        txt_pub = QLineEdit()
        txt_pub.setPlaceholderText("选择公钥文件 (*_public.pem)")
        txt_pub.setReadOnly(True)
        txt_pub.setMinimumHeight(36)
        btn_pub = QPushButton("浏览")
        btn_pub.setMinimumWidth(90)
        btn_pub.setMinimumHeight(36)
        btn_pub.clicked.connect(lambda: self._select_key_file(txt_pub, "公钥"))
        h_pub.addWidget(txt_pub)
        h_pub.addWidget(btn_pub)
        layout.addLayout(h_pub)

        lbl_priv = QLabel("私钥文件:")
        lbl_priv.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_priv)

        h_priv = QHBoxLayout()
        h_priv.setStretch(0, 1)  # 输入框占满剩余空间
        txt_priv = QLineEdit()
        txt_priv.setPlaceholderText("选择私钥文件 (*_private.pem)")
        txt_priv.setReadOnly(True)
        txt_priv.setMinimumHeight(36)
        btn_priv = QPushButton("浏览")
        btn_priv.setMinimumWidth(90)
        btn_priv.setMinimumHeight(36)
        btn_priv.clicked.connect(lambda: self._select_key_file(txt_priv, "私钥"))
        h_priv.addWidget(txt_priv)
        h_priv.addWidget(btn_priv)
        layout.addLayout(h_priv)

        layout.addStretch()

        h_btns = QHBoxLayout()
        h_btns.addStretch()
        btn_ok = QPushButton("导入")
        btn_ok.setFixedWidth(80)
        btn_ok.clicked.connect(lambda: self._do_import_keypair(txt_pub.text(), txt_priv.text(), dialog))
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(dialog.reject)
        h_btns.addWidget(btn_ok)
        h_btns.addWidget(btn_cancel)
        layout.addLayout(h_btns)

        dialog.exec()

    def _select_key_file(self, line_edit, key_type):
        """选择密钥文件"""
        file, _ = QFileDialog.getOpenFileName(self, f"选择{key_type}文件", "", "PEM文件 (*.pem);;所有文件 (*)")
        if file:
            line_edit.setText(file)

    def _do_import_keypair(self, pub_path, priv_path, dialog):
        """执行导入密钥对"""
        if not pub_path or not priv_path:
            return QMessageBox.warning(self, "提示", "请选择公钥和私钥文件")

        if not os.path.exists(pub_path) or not os.path.exists(priv_path):
            return QMessageBox.warning(self, "错误", "文件不存在")

        keys_dir = DIRS["KEYS"]
        pub_name = os.path.basename(pub_path)
        priv_name = os.path.basename(priv_path)

        pub_dest = os.path.join(keys_dir, pub_name)
        priv_dest = os.path.join(keys_dir, priv_name)

        if os.path.exists(pub_dest) or os.path.exists(priv_dest):
            reply = QMessageBox.question(self, "确认", "密钥文件已存在，是否覆盖？")
            if reply != QMessageBox.Yes:
                return

        shutil.copy2(pub_path, pub_dest)
        shutil.copy2(priv_path, priv_dest)

        sys_logger.log(f"导入密钥对: {pub_name}, {priv_name}")
        self.append_log(f"导入密钥对成功")
        self.action_refresh_keys()
        dialog.accept()
        QMessageBox.information(self, "完成", "密钥对导入成功！")

    def action_delete_key(self):
        if not self.use_new_system:
            return QMessageBox.information(self, "提示", "老系统无需管理密钥")

        selected = self.key_list.currentItem()
        if not selected:
            return QMessageBox.warning(self, "提示", "请先选择要删除的密钥对")

        key_name = selected.text().strip()
        if key_name.startswith("密钥对:"):
            key_name = key_name.split(":", 1)[1].strip()
        elif key_name.startswith(("公钥:", "私钥:")):
            key_name = key_name.split(":", 1)[1].strip()
            key_name = key_name.replace("_public.pem", "").replace("_private.pem", "")
        reply = QMessageBox.question(self, "确认删除", f"确定要删除密钥对 {key_name} 吗？\n\n将同时删除私钥和公钥文件！")
        if reply == QMessageBox.Yes:
            try:
                keys_dir = DIRS["KEYS"]
                private_path = os.path.join(keys_dir, f"{key_name}_private.pem")
                public_path = os.path.join(keys_dir, f"{key_name}_public.pem")

                if os.path.exists(private_path):
                    os.remove(private_path)
                if os.path.exists(public_path):
                    os.remove(public_path)

                sys_logger.log(f"删除密钥对: {key_name}")
                self.append_log(f"删除密钥对: {key_name}")
                self.action_refresh_keys()
                QMessageBox.information(self, "完成", "密钥对已删除")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
