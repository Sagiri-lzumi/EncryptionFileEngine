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
                               QListWidgetItem, QFrame, QStackedWidget, QApplication, QCheckBox,
                               QSplitter, QGraphicsDropShadowEffect, QSizePolicy,
                               QSystemTrayIcon, QMenu, QComboBox, QSpacerItem)
from PySide6.QtCore import (QThread, Signal, Qt, QUrl, QPropertyAnimation,
                            QEasingCurve, QRectF, QSize, Property, QPoint, QParallelAnimationGroup)
from PySide6.QtGui import (QDesktopServices, QPainter, QColor, QPen, QFont,
                           QBrush, QIcon, QPainterPath, QCursor, QAction,
                           QGuiApplication)

from config import DIRS
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger
from ui.themes import (
    THEMES,
    CONTROL_HEIGHT,
    THEME_TOGGLE_SIZE,
    THEME_TOGGLE_MARGIN,
)
from ui.native_effects import NativeGlassController
from ui.components import (AnimatedSidebarButton, ModernButton, DragDropListWidget,
                           CustomCheckBox, SmoothScrollArea,
                           DropDownComboBox, SystemSwitchButton, GlassProgressBar,
                           CleanStackedWidget, PageSurface, SectionHeader, IconBadge,
                           TaskWorkspacePanel, InspectorSection, ExecutionFooter,
                           KeyPairListRow, BrandLogoBadge, ThemeToggleButton)
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


class RSABatchWorkerThread(QThread):
    """
    新 RSA 混合加密系统的批量任务线程。

    旧实现直接在 UI 线程循环处理文件，只靠 QApplication.processEvents()
    维持表面响应。这里保持原有输出规则不变，将耗时 I/O 与加解密搬到后台线程，
    并复用现有进度、日志、暂停和终止交互。
    """
    sig_progress = Signal(str, int)
    sig_log = Signal(str)
    sig_finished = Signal(dict)

    def __init__(self, files, is_encrypt, key_path, key_password=None,
                 custom_out_dir=None, encrypt_filename=False):
        super().__init__()
        self.files = files
        self.is_enc = is_encrypt
        self.key_path = key_path
        self.key_password = key_password
        self.custom_out = custom_out_dir
        self.encrypt_filename = encrypt_filename
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()

    def _wait_if_paused(self):
        while not self._stop_event.is_set() and not self._pause_event.is_set():
            QThread.msleep(80)

    def run(self):
        from core.rsa_cipher import RSAFileCipher
        import uuid

        results = {"success": [], "fail": []}
        valid_files = []
        total_bytes = 0

        self.sig_log.emit("--- 正在扫描 RSA 任务队列 ---")
        for file_path in self.files:
            file_path_long = ensure_long_path(file_path)
            if not os.path.exists(file_path_long):
                results["fail"].append((file_path, "文件不存在"))
                continue
            if not os.path.isfile(file_path_long):
                results["fail"].append((file_path, "不是有效文件"))
                continue
            try:
                total_bytes += max(os.path.getsize(file_path_long), 1)
                valid_files.append(file_path)
            except OSError as exc:
                results["fail"].append((file_path, f"无法读取文件大小: {exc}"))

        if not valid_files:
            self.sig_finished.emit(results)
            return

        processed_before_file = 0
        total_count = len(valid_files)

        for index, file_path in enumerate(valid_files, start=1):
            if self._stop_event.is_set():
                break

            self._wait_if_paused()
            if self._stop_event.is_set():
                break

            file_path_long = ensure_long_path(file_path)
            try:
                file_size = max(os.path.getsize(file_path_long), 1)
            except OSError as exc:
                results["fail"].append((file_path, f"无法读取文件大小: {exc}"))
                continue
            fname = os.path.basename(file_path)
            out_dir = self.custom_out if self.custom_out else os.path.dirname(file_path)
            try:
                os.makedirs(ensure_long_path(out_dir), exist_ok=True)
            except OSError as exc:
                results["fail"].append((file_path, f"输出目录不可用: {exc}"))
                processed_before_file += file_size
                continue

            if self.is_enc:
                out_name = f"{uuid.uuid4().hex[:12]}.enc" if self.encrypt_filename else f"{fname}.enc"
                out_path = os.path.join(out_dir, out_name)
            else:
                out_path = os.path.join(out_dir, fname.replace(".enc", ""))

            def progress_callback(current, total, done_before=processed_before_file, source_size=file_size):
                if self._stop_event.is_set():
                    raise InterruptedError("用户终止任务")
                self._wait_if_paused()
                visible_total = max(total or source_size, 1)
                current_bytes = min(max(current, 0), visible_total)
                pct = int(((done_before + current_bytes) / max(total_bytes, 1)) * 100)
                self.sig_progress.emit(f"处理中... {index}/{total_count}", min(pct, 99))

            try:
                if self.is_enc:
                    success, msg = RSAFileCipher.encrypt_file(
                        file_path_long, ensure_long_path(out_path), self.key_path, callback=progress_callback
                    )
                else:
                    result = RSAFileCipher.decrypt_file(
                        file_path_long, ensure_long_path(out_path), self.key_path,
                        self.key_password, callback=progress_callback
                    )
                    if len(result) == 3:
                        success, msg, actual_out_path = result
                        if success:
                            out_path = actual_out_path
                    else:
                        success, msg = result[0], result[1]

                if self._stop_event.is_set():
                    break
                if success:
                    results["success"].append((file_path, out_path))
                    self.sig_log.emit(f"✅ {fname}")
                else:
                    results["fail"].append((file_path, msg))
                    self.sig_log.emit(f"❌ {fname}: {msg}")
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                results["fail"].append((file_path, str(exc)))
                self.sig_log.emit(f"❌ {fname}: {exc}")
            finally:
                processed_before_file += file_size
                pct = int((processed_before_file / max(total_bytes, 1)) * 100)
                self.sig_progress.emit(f"处理中... {min(index, total_count)}/{total_count}", min(pct, 99))

        msg = "已终止" if self._stop_event.is_set() else "任务完成"
        self.sig_progress.emit(msg, 100)
        self.sig_finished.emit(results)


# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Security Engine Enterprise")
        self.setFixedSize(1200, 850)

        self.theme_names = list(THEMES.keys())
        # 默认跟随系统主题：系统 Dark → Dark，Light/Unknown → Light
        self.current_theme_idx = self._system_scheme_theme_idx()
        self.theme_data = THEMES[self.theme_names[self.current_theme_idx]]

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

        # 创建系统托盘
        self._init_tray()

        self._init_ui()
        self.apply_theme()

        # 始终跟随系统主题：系统深浅变化时纠正回系统主题（覆盖手动临时预览）。
        style_hints = QGuiApplication.styleHints()
        try:
            style_hints.colorSchemeChanged.connect(self._on_system_scheme_changed)
        except Exception:
            # 旧 Qt 无此信号时静默降级，保持启动时检测到的主题不崩。
            pass

    @staticmethod
    def _system_scheme_theme_idx(names=None):
        """根据系统 colorScheme 返回主题索引：Dark→Dark，其它(Light/Unknown)→Light。"""
        names = names if names is not None else list(THEMES.keys())
        try:
            scheme = QGuiApplication.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                return names.index("Dark") if "Dark" in names else 0
        except Exception:
            pass
        return names.index("Light") if "Light" in names else 0

    def _on_system_scheme_changed(self, _scheme=None):
        """系统主题变化 → 始终纠正回系统主题（手动预览被覆盖）。"""
        new_idx = self._system_scheme_theme_idx()
        if new_idx != self.current_theme_idx:
            self.current_theme_idx = new_idx
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
        # 确保侧栏 QSS 半透明 background 由该 widget 自绘而非透出父级；
        # 切主题时半透明旧像素才不会残在透出区形成“底色发暗/发灰”残影。
        # 姿势与 components.py ContentStack(WA_StyledBackground)一致。
        self.sidebar.setAttribute(Qt.WA_StyledBackground, True)

        v_sidebar = QVBoxLayout(self.sidebar)
        v_sidebar.setContentsMargins(14, 22, 14, 18)
        v_sidebar.setSpacing(7)

        # 标题（线形盾锁徽标 + 两行品牌名，避免长名在窄侧栏中被裁字）
        title_row = QWidget()
        h_title = QHBoxLayout(title_row)
        h_title.setContentsMargins(0, 0, 0, 0)
        h_title.setSpacing(8)
        logo_badge = BrandLogoBadge(size=30)
        h_title.addWidget(logo_badge, 0, Qt.AlignVCenter)

        text_col = QWidget()
        v_text = QVBoxLayout(text_col)
        v_text.setContentsMargins(0, 0, 0, 0)
        v_text.setSpacing(0)
        lbl_title = QLabel("Encryption")
        lbl_title.setObjectName("AppTitle")
        lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl_subtitle = QLabel("Studio")
        lbl_subtitle.setObjectName("AppSubtitle")
        lbl_subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        v_text.addWidget(lbl_title)
        v_text.addWidget(lbl_subtitle)
        h_title.addWidget(text_col, 1, Qt.AlignVCenter)
        v_sidebar.addWidget(title_row)

        lbl_nav = QLabel("WORKSPACE")
        lbl_nav.setObjectName("SidebarGroupLabel")
        v_sidebar.addSpacing(20)
        v_sidebar.addWidget(lbl_nav)

        # 导航按钮
        self.btn_nav_enc = AnimatedSidebarButton("加密", "lock", self)
        self.btn_nav_dec = AnimatedSidebarButton("解密", "unlock", self)
        self.btn_nav_key = AnimatedSidebarButton("密钥", "key", self)
        self.btn_nav_log = AnimatedSidebarButton("日志", "doc", self)

        # 按钮组逻辑
        self.btn_nav_enc.clicked.connect(lambda: self.switch_page(0))
        self.btn_nav_dec.clicked.connect(lambda: self.switch_page(1))
        self.btn_nav_key.clicked.connect(lambda: self.switch_page(2))
        self.btn_nav_log.clicked.connect(lambda: self.switch_page(3))

        self.sidebar_btns = [self.btn_nav_enc, self.btn_nav_dec, self.btn_nav_key, self.btn_nav_log]
        for btn in self.sidebar_btns:
            v_sidebar.addWidget(btn)
        self.btn_nav_enc.set_selected(True, animate=False)

        v_sidebar.addStretch()

        # 版本信息
        lbl_version = QLabel("v1.0 nexus")
        lbl_version.setAlignment(Qt.AlignCenter)
        lbl_version.setObjectName("VersionLabel")
        v_sidebar.addWidget(lbl_version)

        main_layout.addWidget(self.sidebar)

        # === 2. 右侧内容区（内容栈直接占满，切换器悬浮右上角）===
        right_area = QWidget()
        right_area.setObjectName("RightArea")
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.content_stack = CleanStackedWidget()
        right_layout.addWidget(self.content_stack, 1)
        main_layout.addWidget(right_area, 1)

        # 日/月切换器：悬浮覆盖层，浮在右侧内容区右上角、不占布局高度。
        # 不放进任何 layout（否则会挤占内容区），以 right_area 为父手动 move()
        # 定位，并跟随窗口 resize/show 更新位置 → 真正回到"右上角"而非横栏右端。
        self._theme_toggle_host = right_area
        self.btn_theme_toggle = ThemeToggleButton()
        self.btn_theme_toggle.setParent(right_area)
        self.btn_theme_toggle.raise_()
        # 点击：临时切到另一主题预览（系统的 colorSchemeChanged 到来时再纠正回系统主题）
        self.btn_theme_toggle.clicked.connect(self._toggle_theme_preview)
        self._position_theme_toggle()

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
        log_action.triggered.connect(lambda: self.show_and_switch(3))
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
        self._position_theme_toggle()

    def resizeEvent(self, event):
        """窗口缩放时同步右上角悬浮切换器位置。"""
        super().resizeEvent(event)
        self._position_theme_toggle()

    def _position_theme_toggle(self):
        """把日/月主题切换器贴到右侧内容区右上角（overlay，不占布局高度）。

        切换器以 right_area 为父、手动 move：x = 宽度 - 自身宽 - 右边距，y = 顶边距。
        首次布局完成前 right_area 尺寸可能为 0，用 max 兜底避免负坐标。窗口
        resize/show 后再各调一次，最终落到右上角。
        """
        host = getattr(self, "_theme_toggle_host", None)
        btn = getattr(self, "btn_theme_toggle", None)
        if host is None or btn is None:
            return
        margin = THEME_TOGGLE_MARGIN          # 与右上避让同源（ui.themes）
        w = max(btn.width(), 1)
        x = max(0, host.width() - w - margin)
        y = margin
        btn.move(x, y)
        btn.raise_()

    def switch_page(self, index):
        """切换页面"""
        if index == self.content_stack.currentIndex():
            return

        old_index = self.content_stack.currentIndex()
        old_page = self.content_stack.currentWidget()
        if old_page:
            old_page.clearFocus()
            old_page.update()

        self.content_stack.setCurrentIndex(index)
        new_page = self.content_stack.currentWidget()
        if new_page:
            new_page.update()
            new_page.repaint()
        self.content_stack.update()
        self.content_stack.repaint()

        for i in (old_index, index):
            if 0 <= i < len(self.sidebar_btns):
                self.sidebar_btns[i].set_selected(i == index, animate=True)

    def _create_common_layout(self, is_encrypt):
        page = PageSurface()
        # 使用 Splitter 允许用户调整左右比例
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: transparent;
            }
        """)

        # === 左侧：任务队列工作台 ===
        task_title = "加密任务工作台" if is_encrypt else "解密任务工作台"
        task_subtitle = "添加待加密文件，配置输出与安全策略" if is_encrypt else "添加加密包，配置解密输出策略"
        left_container = TaskWorkspacePanel(task_title, task_subtitle, "lock" if is_encrypt else "unlock")
        v_left = left_container.content_layout()

        # 系统状态提示
        h_status = QHBoxLayout()
        h_status.setContentsMargins(0, 0, 0, 10)
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

        file_list = DragDropListWidget()
        file_list.setObjectName("TaskQueueList")
        file_list.queue_changed.connect(lambda: self.update_queue_count(is_encrypt))
        v_left.addWidget(file_list, 1)

        # 按钮栏
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_add = ModernButton("添加文件", "normal", "file-plus")
        btn_add.clicked.connect(lambda: self.action_add_file(is_encrypt))
        self.all_buttons.append(btn_add)

        btn_add_folder = ModernButton("添加目录", "normal", "folder-plus")
        btn_add_folder.clicked.connect(lambda: self.action_add_folder(is_encrypt))
        self.all_buttons.append(btn_add_folder)

        btn_del = ModernButton("移除选中", "normal", "remove")
        btn_del.clicked.connect(lambda: self.action_remove_file(file_list, is_encrypt))
        self.all_buttons.append(btn_del)

        btn_clr = ModernButton("清空", "normal", "clear")
        btn_clr.clicked.connect(lambda: (file_list.clear(), self.update_queue_count(is_encrypt), self.reset_ui_state(is_encrypt)))
        self.all_buttons.append(btn_clr)

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_add_folder)
        btn_bar.addStretch()
        btn_bar.addWidget(btn_del)
        btn_bar.addWidget(btn_clr)

        left_container.footer_layout().addLayout(btn_bar)
        splitter.addWidget(left_container)

        # === 右侧：配置面板 (毛玻璃卡片) ===
        right_container = QFrame()
        right_container.setObjectName("ConfigPanel")
        # 放宽配置面板宽度上下限，让「输出路径」「高级策略」等路径输入框不被挤窄。
        # 旧值 minWidth380/maxWidth500 时路径框只剩下 ~280px 可读宽度。
        right_container.setMinimumWidth(420)
        right_container.setMaximumWidth(640)

        v_right = QVBoxLayout(right_container)
        v_right.setContentsMargins(0, 0, 0, 0)
        v_right.setSpacing(0)

        # 标题区域 - 固定在顶部 (紧凑)
        title_area = QWidget()
        title_area.setObjectName("ConfigTitleArea")
        title_area.setFixedHeight(58)
        v_title = QVBoxLayout(title_area)
        v_title.setContentsMargins(16, 10, 16, 10)
        v_title.addWidget(SectionHeader("任务检查器", "advanced"))
        v_right.addWidget(title_area)

        # === 可滚动配置区域 ===
        scroll_area = SmoothScrollArea()
        scroll_area.setObjectName("ConfigScrollArea")
        scroll_area.setMinimumHeight(200)

        # 滚动内容容器
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        # 启用样式背景，使 QSS background:transparent 生效，
        # 避免非 macOS 关玻璃时配置滚动内容冒系统浅色块。
        scroll_content.setAttribute(Qt.WA_StyledBackground, True)
        v_scroll = QVBoxLayout(scroll_content)
        v_scroll.setContentsMargins(16, 0, 16, 12)
        v_scroll.setSpacing(10)  # 减小间距

        def create_config_section(title, icon_name):
            card = InspectorSection(title, icon_name)
            return card, card.content_layout()

        # 1. 安全设置
        grp_sec, v_sec = create_config_section("安全凭证", "credential")

        # 老系统：密码输入
        self.old_sec_widget = QWidget() if is_encrypt else QWidget()
        v_old_sec = QVBoxLayout(self.old_sec_widget)
        v_old_sec.setContentsMargins(0, 0, 0, 0)
        txt_pwd = QLineEdit()
        txt_pwd.setEchoMode(QLineEdit.Password)
        txt_pwd.setPlaceholderText("输入密码...")
        txt_pwd.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
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
            combo_key.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
            v_new_sec.addWidget(combo_key)
        else:
            lbl_key = QLabel("选择私钥（用于解密）:")
            lbl_key.setObjectName("InputLabel")
            v_new_sec.addWidget(lbl_key)
            combo_key = DropDownComboBox()
            combo_key.setPlaceholderText("选择私钥...")
            combo_key.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
            v_new_sec.addWidget(combo_key)
            txt_key_pwd = QLineEdit()
            txt_key_pwd.setEchoMode(QLineEdit.Password)
            txt_key_pwd.setPlaceholderText("输入私钥密码...")
            txt_key_pwd.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
            v_new_sec.addWidget(txt_key_pwd)

        v_sec.addWidget(self.new_sec_widget)
        self.new_sec_widget.hide()
        v_scroll.addWidget(grp_sec)

        # 2. 输出设置
        grp_io, v_io = create_config_section("输出路径", "output")

        h_path = QHBoxLayout()
        h_path.setSpacing(8)
        txt_path = QLineEdit()
        txt_path.setPlaceholderText("源文件目录")
        txt_path.setToolTip("未选择输出目录时，结果会生成在源文件所在目录")
        txt_path.setReadOnly(True)
        txt_path.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
        h_path.addWidget(txt_path, 1)

        btn_path = ModernButton("浏览", "normal", "browse")
        btn_path.setMinimumWidth(80)  # 自适应宽度，最小80px
        # 高度由 QSS(ModernButton#normal min-height = control_height)统一，不再 setFixedHeight
        btn_path.clicked.connect(lambda: self.action_select_dir(is_encrypt))
        self.all_buttons.append(btn_path)
        h_path.addWidget(btn_path)

        btn_path_reset = ModernButton("默认", "normal", "back")
        btn_path_reset.setMinimumWidth(72)
        # 高度由 QSS(control_height)统一
        btn_path_reset.setToolTip("恢复为源文件所在目录")
        btn_path_reset.clicked.connect(lambda: self.action_clear_dir(is_encrypt))
        self.all_buttons.append(btn_path_reset)
        h_path.addWidget(btn_path_reset)
        v_io.addLayout(h_path)

        # 保留目录结构
        chk_struct = CustomCheckBox("保留目录结构")
        chk_struct.setEnabled(False)
        chk_struct.setToolTip("选择自定义输出目录后可用")
        v_io.addWidget(chk_struct)

        # 加密/解密文件名
        chk_dir_name_enc = None
        if is_encrypt:
            chk_dir_name_enc = CustomCheckBox("加密文件夹名")
            chk_dir_name_enc.setEnabled(False)
            chk_dir_name_enc.setToolTip("启用保留目录结构后可用")
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
            chk_dir_name_enc.setToolTip("启用保留目录结构后可用")
            v_io.addWidget(chk_dir_name_enc)

            def on_struct_toggled_dec(state):
                is_checked = (state == 2)
                if chk_dir_name_enc:
                    chk_dir_name_enc.setEnabled(is_checked)
                    if not is_checked: chk_dir_name_enc.setChecked(False)

            chk_struct.stateChanged.connect(on_struct_toggled_dec)

        v_scroll.addWidget(grp_io)

        # 3. 高级选项
        grp_adv, v_adv = create_config_section("高级策略", "advanced")

        h_ssd = QHBoxLayout()
        h_ssd.setSpacing(8)
        txt_ssd = QLineEdit()
        txt_ssd.setPlaceholderText("选择 SSD 缓存路径...")
        txt_ssd.setToolTip("旧系统可使用 SSD 路径作为临时缓存")
        txt_ssd.setReadOnly(True)
        txt_ssd.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
        h_ssd.addWidget(txt_ssd, 1)

        btn_ssd = ModernButton("选择", "normal", "browse")
        btn_ssd.setMinimumWidth(80)  # 自适应宽度最小80px
        # 高度由 QSS(control_height)统一
        btn_ssd.clicked.connect(lambda: self.action_select_ssd(is_encrypt))
        self.all_buttons.append(btn_ssd)
        h_ssd.addWidget(btn_ssd)

        btn_ssd_reset = ModernButton("清除", "normal", "clear")
        btn_ssd_reset.setMinimumWidth(72)
        # 高度由 QSS(control_height)统一
        btn_ssd_reset.setToolTip("清除 SSD 缓存路径")
        btn_ssd_reset.clicked.connect(self.action_clear_ssd)
        self.all_buttons.append(btn_ssd_reset)
        h_ssd.addWidget(btn_ssd_reset)
        v_adv.addLayout(h_ssd)

        chk_ssd = CustomCheckBox("启用 SSD 加速")
        chk_ssd.setEnabled(False)
        chk_ssd.setToolTip("选择 SSD 缓存路径后可用")
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

        # === 底部执行区 - 固定在底部 ===
        execution_footer = ExecutionFooter()
        lbl_status = execution_footer.status_label
        pbar = execution_footer.progress_bar
        stack = execution_footer.actions_stack

        # Start
        w_start = QWidget()
        l_start = QHBoxLayout(w_start)
        l_start.setContentsMargins(0, 0, 0, 0)
        btn_run = ModernButton(f"开始{'加密' if is_encrypt else '解密'}", "primary", "play")
        btn_run.setFixedHeight(48)
        btn_run.clicked.connect(self.run_encrypt if is_encrypt else self.run_decrypt)
        self.all_buttons.append(btn_run)
        l_start.addWidget(btn_run)
        stack.addWidget(w_start)

        # Running
        w_ctrl = QWidget()
        l_ctrl = QHBoxLayout(w_ctrl)
        l_ctrl.setContentsMargins(0, 0, 0, 0)
        l_ctrl.setSpacing(8)
        btn_pause = ModernButton("挂起", "normal", "pause")
        btn_pause.setFixedHeight(44)
        btn_pause.clicked.connect(self.action_toggle_pause)
        self.all_buttons.append(btn_pause)
        btn_stop = ModernButton("终止", "danger", "stop")
        btn_stop.setFixedHeight(44)
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
        btn_open = ModernButton("打开目录", "normal", "open-folder")
        btn_open.setFixedHeight(44)
        btn_open.clicked.connect(self.action_open_folder)
        self.all_buttons.append(btn_open)
        btn_back = ModernButton("返回", "normal", "back")
        btn_back.setFixedHeight(44)
        btn_back.clicked.connect(lambda: self.reset_ui_state(is_encrypt))
        self.all_buttons.append(btn_back)
        l_res.addWidget(btn_open)
        l_res.addWidget(btn_back)
        stack.addWidget(w_res)

        v_right.addWidget(execution_footer)

        splitter.addWidget(right_container)

        # 设置 Splitter 比例：略偏右配置面板，让路径输入框开局即有足够宽度。
        # 旧权重 6:4 在窗口不宽时会把右面板压到 minWidth，路径框很窄。
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        # 给一个初始可见宽度，保证首次进入时右面板不至于被压到 maxWidth 下限附近。
        splitter.setSizes([620, 640])

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
            "btn_add": btn_add, "btn_add_folder": btn_add_folder,
            "btn_del": btn_del, "btn_clr": btn_clr,
            "btn_path": btn_path, "btn_path_reset": btn_path_reset,
            "btn_ssd": btn_ssd, "btn_ssd_reset": btn_ssd_reset,
            "btn_run": btn_run,
            "queue_panel": left_container,
            "execution_footer": execution_footer,
            "old_sec_widget": self.old_sec_widget,
            "new_sec_widget": self.new_sec_widget,
            "combo_key": combo_key,
            "txt_key_pwd": txt_key_pwd if not is_encrypt else None,
            "scroll_area": scroll_area,
            "delete_confirmed": False
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
        page = PageSurface()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("ContentPanel")
        v = QVBoxLayout(container)
        self.key_page_layout = v
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(20)

        v.addWidget(SectionHeader("密钥管理中心", "key"))

        # 系统切换卡片 (紧凑布局)
        switch_card = QFrame()
        switch_card.setObjectName("SwitchCard")
        switch_card.setFixedHeight(78)
        h_switch = QHBoxLayout(switch_card)
        h_switch.setContentsMargins(18, 14, 18, 14)
        h_switch.setSpacing(14)

        self.system_icon_badge = IconBadge("key", 44, accent=True)
        h_switch.addWidget(self.system_icon_badge)

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
        self.btn_switch_system.setFixedSize(170, 36)
        self.btn_switch_system.clicked.connect(self.action_switch_system)
        h_switch.addWidget(self.btn_switch_system)
        v.addWidget(switch_card)

        # 密钥列表标题
        self.key_list_header = SectionHeader("密钥列表", "doc")
        v.addWidget(self.key_list_header)

        self.key_list = QListWidget()
        self.key_list.setObjectName("KeyPairList")
        self.key_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.key_list.setMinimumHeight(180)
        self.key_list.setMaximumHeight(260)
        v.addWidget(self.key_list)

        # 老系统提示
        self.old_system_widget = QFrame()
        self.old_system_widget.setObjectName("KeyInfoPanel")
        self.old_system_widget.setMaximumHeight(88)
        v_old = QVBoxLayout(self.old_system_widget)
        v_old.setContentsMargins(16, 14, 16, 14)
        lbl_old_tip = QLabel("老系统使用对称加密，加密时直接输入密码即可，无需预先生成密钥")
        lbl_old_tip.setObjectName("InfoTip")
        lbl_old_tip.setWordWrap(True)
        v_old.addWidget(lbl_old_tip)
        v.addWidget(self.old_system_widget)

        # 新系统输入框 (紧凑布局)
        self.new_system_widget = QFrame()
        self.new_system_widget.setObjectName("KeyActionPanel")
        self.new_system_widget.setMaximumHeight(114)
        v_new = QVBoxLayout(self.new_system_widget)
        v_new.setContentsMargins(16, 14, 16, 14)
        v_new.setSpacing(10)

        v_new.addWidget(SectionHeader("生成新密钥对", "generate"))

        h_new = QHBoxLayout()
        h_new.setSpacing(10)
        self.new_key_name_input = QLineEdit()
        self.new_key_name_input.setPlaceholderText("密钥对名称 (例如: my_key)")
        self.new_key_name_input.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
        self.new_key_password_input = QLineEdit()
        self.new_key_password_input.setPlaceholderText("保护密码")
        self.new_key_password_input.setEchoMode(QLineEdit.Password)
        self.new_key_password_input.setFixedHeight(CONTROL_HEIGHT)  # 控件高度统一（ui.themes.CONTROL_HEIGHT）
        h_new.addWidget(self.new_key_name_input, 2)
        h_new.addWidget(self.new_key_password_input, 1)
        v_new.addLayout(h_new)
        v.addWidget(self.new_system_widget)
        self.new_system_widget.hide()

        # 按钮栏 (紧凑布局)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_gen_new = ModernButton("生成密钥对", "primary", "generate")
        # 高度由 QSS(primary = control_primary_height 48px)统一，不再强制 34
        self.btn_gen_new.clicked.connect(self.action_generate_keypair)
        self.all_buttons.append(self.btn_gen_new)
        self.btn_gen_new.hide()

        self.btn_import_new = ModernButton("导入", "normal", "import")
        # 高度由 QSS(normal = control_height)统一
        self.btn_import_new.clicked.connect(self.action_import_keypair)
        self.all_buttons.append(self.btn_import_new)
        self.btn_import_new.hide()

        self.btn_delete_key = ModernButton("删除", "danger", "trash")
        # 高度由 QSS(danger = control_primary_height)统一
        self.btn_delete_key.clicked.connect(self.action_delete_key)
        self.all_buttons.append(self.btn_delete_key)

        self.btn_refresh_keys = ModernButton("刷新", "normal", "refresh")
        # 高度由 QSS(normal = control_height)统一
        self.btn_refresh_keys.clicked.connect(self.action_refresh_keys)
        self.all_buttons.append(self.btn_refresh_keys)

        btn_bar.addWidget(self.btn_gen_new)
        btn_bar.addWidget(self.btn_import_new)
        btn_bar.addWidget(self.btn_delete_key)
        btn_bar.addWidget(self.btn_refresh_keys)
        btn_bar.addStretch()

        v.addLayout(btn_bar)
        self.key_page_bottom_spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        v.addItem(self.key_page_bottom_spacer)
        layout.addWidget(container)
        self.content_stack.addWidget(page)
        self.action_refresh_keys()

    def _init_page_log(self):
        page = PageSurface()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("ContentPanel")
        v = QVBoxLayout(container)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        v.addWidget(SectionHeader("系统运行日志", "log"))

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setObjectName("LogTextEdit")
        v.addWidget(self.txt_log)

        layout.addWidget(container)
        self.content_stack.addWidget(page)

    def on_theme_selected(self, theme_name):
        """主题被选中"""
        self.current_theme_idx = self.theme_names.index(theme_name)
        self.apply_theme()

    def _toggle_theme_preview(self):
        """点击太阳/月亮：临时切到另一主题预览（不持久）。

        始终跟随系统：系统 colorSchemeChanged 到来时 _on_system_scheme_changed
        会将其纠正回系统主题，故此处仅为预览体验。
        """
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.theme_names)
        self.apply_theme()

    def apply_theme(self):
        """应用 mac-first Liquid Glass 主题。"""
        theme_name = self.theme_names[self.current_theme_idx]
        t = THEMES[theme_name]
        self.theme_data = t
        native_glass_enabled = self.native_glass.apply(t)
        window_bg = "transparent" if native_glass_enabled else t["bg"]
        main_surface_bg = "transparent" if native_glass_enabled else t["bg"]

        self.setAttribute(Qt.WA_TranslucentBackground, native_glass_enabled)
        self.setAutoFillBackground(not native_glass_enabled)
        self.main_surface.setAttribute(Qt.WA_TranslucentBackground, native_glass_enabled)
        self.main_surface.setAutoFillBackground(not native_glass_enabled)

        for widget in self.findChildren(QLineEdit):
            widget.setTextMargins(10, 0, 10, 0)

        qss = f"""
        QMainWindow {{
            background: {window_bg};
        }}
        QWidget#MainSurface {{
            background: {main_surface_bg};
        }}
        QStackedWidget#ContentStack {{
            background: transparent;
            border: none;
        }}
        QFrame#PageSurface {{
            background: transparent;
            border: none;
        }}
        QWidget {{
            color: {t['fg']};
            font-family: {get_system_font_qss()};
            font-size: {t['body_size']};
            font-weight: {t['body_weight']};
        }}
        /* 兜底：这些中间容器都嵌在已设深色背景的父容器里（ConfigPanel/InspectorSection/
           TaskWorkspacePanel/ConfigPanelCard）。显式标 transparent 并启用样式背景，
           避免非 macOS 平台关闭毛玻璃后 Qt 用系统默认浅色 autoFillBackground，
           在深色面板里冒出白/灰块、形成 Dark 模式黑白不统一。 */
        QWidget#ScrollContent,
        QWidget#InspectorSectionContent,
        QWidget#WorkspaceBody,
        QWidget#CardContent,
        QWidget#BottomArea,
        QWidget#WorkspaceToolbar {{
            background: transparent;
        }}
        /* 滚动区 viewport 兜底，防止配置滚动区视口冒系统色。 */
        QScrollArea#ConfigScrollArea,
        QScrollArea#ConfigScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        /* 右侧内容区容器：透明，透出 main_surface bg，避免 dark 下冒系统色条。切换器
           以 overlay 浮于其上，自身在 ThemeToggleButton.paintEvent 已清底透明。 */
        QWidget#RightArea {{
            background: transparent;
        }}
        /* 主题切换器是自绘 paintEvent 的 QPushButton：paintEvent 已用
           CompositionMode_Source 清底透明、仅画图标+hover 淡圆。但 QPushButton 的
           native 默认底+边框不被 paintEvent 覆盖，会先画一圈方形不透明底冒成“突兀方块”。
           这里用 objectName 规则关掉 native 底与边框，透出玻璃，方块消失。 */
        QPushButton#ThemeToggleButton {{
            background: transparent;
            border: none;
        }}

        QFrame#Sidebar {{
            background: {t['sidebar']};
            /* 四角统一单一 border：叠 border-bottom 改色会使圆角弧线在底两角
               颜色/粗细断裂(Dark 下尤甚),观感像底部两角是直的/有方块。
               去叠底边,立体感由容器自绘阴影承担。*/
            border: 1px solid {t['glass_border']};
            border-radius: {t['radius_lg']};
        }}
        QLabel#AppTitle {{
            color: {t['fg']};
            font-size: {t.get('title_size', '16px')};
            font-weight: 800;
        }}
        QLabel#AppSubtitle {{
            color: {t['fg_tertiary']};
            font-size: {t.get('caption_size', '11px')};
            font-weight: 500;
        }}
        QLabel#VersionLabel {{
            color: {t['fg_tertiary']};
            font-size: {t.get('caption_size', '11px')};
            font-weight: 500;
        }}
        QLabel#SidebarGroupLabel {{
            color: {t['fg_tertiary']};
            font-size: {t.get('micro_size', '10px')};
            font-weight: 800;
            padding: 0 8px 4px 8px;
        }}

        QFrame#ContentPanel {{
            background: {t['panel_elevated']};
            border: 1px solid {t['glass_border']};
            border-radius: {t['radius_lg']};
        }}
        QFrame#TaskWorkspacePanel {{
            background: {t['panel_elevated']};
            border: 1px solid {t['glass_border']};
            border-radius: {t.get('radius_panel', '14px')};
        }}
        QLabel#WorkspaceTitle {{
            color: {t['fg']};
            font-size: {t.get('title_size', '16px')};
            font-weight: 800;
        }}
        QLabel#WorkspaceSubtitle {{
            color: {t['fg_secondary']};
            font-size: {t.get('subtitle_size', '12px')};
            font-weight: 500;
        }}
        QLabel#QueueCounter {{
            /* 语义药丸：与 SystemBadge/SystemGlyph 同款 accent 语系，
               统一"待处理文件数 / 系统徽标 / 系统字标"三者的视觉语系，
               取代原先中性 surface + border 的孤立配色。 */
            color: {t['accent']};
            background: {t['accent_light']};
            border: 1px solid {t['sidebar_active_border']};
            border-radius: {t.get('radius_pill', '9px')};  /* 与 SystemBadge/KeyPairStatus 同款半圆药丸端 */
            padding: 4px 11px;
            font-size: {t.get('caption_size', '11px')};
            font-weight: 700;
        }}
        QWidget#WorkspaceToolbar {{
            background: transparent;
            border-top: 1px solid {t['separator']};
            padding-top: 10px;
        }}

        QFrame#ConfigPanel {{
            background: {t['panel_elevated']};
            border: 1px solid {t['config_panel_border']};
            border-radius: {t.get('radius_panel', '14px')};
        }}
        QWidget#ConfigTitleArea {{
            background: transparent;
            border-bottom: 1px solid {t['separator']};
        }}
        QWidget#BottomArea {{
            background: transparent;
            border-top: 1px solid {t['separator']};
        }}
        QFrame#ExecutionFooter {{
            background: {t['panel_elevated']};
            border-top: 1px solid {t['separator']};
            /* 统一四角圆角：只设 border-top 时上面两角属预期直角分线,
               但底部两角必须圆且与父 TaskWorkspacePanel(radius_panel)对齐;
               原来仅设底两角 10px 既错位(父 14px)又使中间段无 radius 渲染为直角。*/
            border-radius: {t.get('radius_panel', '14px')};
        }}
        QStackedWidget#ExecutionActions {{
            background: transparent;
            border: none;
        }}
        QLabel#ExecutionTitle {{
            color: {t['fg_secondary']};
            font-size: {t.get('subtitle_size', '12px')};
            font-weight: 700;
        }}

        QLabel#SectionTitle {{
            color: {t['fg']};
            font-size: {t['section_title_size']};
            font-weight: {t['section_title_weight']};
        }}
        QLabel#SubSectionTitle {{
            color: {t['fg_secondary']};
            font-size: {t.get('subtitle_size', '12px')};
            font-weight: 600;
        }}
        QWidget#SectionHeader {{
            background: transparent;
        }}
        QLabel#SectionHeaderTitle {{
            color: {t['fg']};
            font-size: {t.get('label_size', '13px')};
            font-weight: 700;
        }}
        QLabel#InputLabel {{
            color: {t['fg_secondary']};
            font-size: {t.get('subtitle_size', '12px')};
            font-weight: 500;
        }}
        QLabel#SystemBadge {{
            color: {t['accent']};
            font-weight: 600;
            font-size: {t.get('caption_size', '11px')};
            background: {t['accent_light']};
            padding: 4px 11px;
            border-radius: {t.get('radius_pill', '9px')};  /* 与 QueueCounter/KeyPairStatus 同款半圆药丸端 */
            border: 1px solid {t['sidebar_active_border']};
        }}

        QPushButton {{
            background: {t['panel']};
            /* 四角统一 border：叠 border_dark 底边使圆角弧线在底两角颜色突变
               (Dark 下 0.34 vs 0.13 差异巨大),底部两角观感变直/有方块。
               删叠底边,四角弧线一致。*/
            border: 1px solid {t['border']};
            border-radius: {t['radius_sm']};
            color: {t['fg']};
            padding: 8px 18px;
            font-size: {t.get('label_size', '13px')};
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
            border-radius: {t['radius_md']};
            color: {t['fg']};
            padding: 0 14px;
            font-size: {t.get('label_size', '13px')};
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
            min-height: {t.get('combo_height', '40px')};
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
            border-radius: {t['radius_md']};
            margin-top: 20px;
            padding: 18px 14px 14px 14px;
            font-weight: 600;
            font-size: {t.get('subtitle_size', '12px')};
            color: {t['fg']};
        }}
        QGroupBox#GlassGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 16px;
            padding: 0 8px;
            color: {t['fg_secondary']};
        }}

        QFrame#ConfigSection,
        QFrame#InspectorSection {{
            background: {t['surface']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t.get('radius_md', '10px')};
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
            font-size: {t.get('subtitle_size', '12px')};
            font-weight: 600;
        }}
        QWidget#CardContent {{
            background: transparent;
        }}

        QFrame#StatusContainer {{
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_md']};
        }}
        QLabel#StatusLabel {{
            color: {t['fg_secondary']};
        }}

        QListWidget {{
            background: {t['list_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_md']};
            padding: 6px;
            outline: none;
        }}
        QListWidget#TaskQueueList {{
            background: {t['list_bg']};
            border: 1px solid {t['border']};
            border-radius: {t.get('radius_list', '12px')};
            padding: 8px;
        }}
        QListWidget#KeyPairList {{
            background: {t['list_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t.get('radius_list', '12px')};
            padding: 6px;
        }}
        QListWidget::item {{
            border-radius: {t.get('radius_sm', '8px')};
            padding: 10px 14px;
            margin: 3px 4px;
            color: {t['fg']};
        }}
        QListWidget#KeyPairList::item {{
            padding: 0;
            margin: 3px 2px;
            border-radius: {t.get('radius_md', '10px')};
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
            border-radius: 3px;  /* 高度 6px 的半圆端(radius=height/2),比例约束,保留字面 */
            text-align: center;
            height: 6px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {t['accent']}, stop:1 {t['accent_hover']});
            border-radius: 3px;
        }}
        /* 进度条轨道高 6px、圆角 3px = 高/2 的半圆形端，比例约束故保留字面而非 token。 */

        QCheckBox {{
            spacing: 10px;
            color: {t['fg']};
            font-size: {t.get('label_size', '13px')};
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: {t.get('radius_xs', '6px')};
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
            border-radius: {t['radius_md']};
        }}
        QFrame#KeyInfoPanel,
        QFrame#KeyActionPanel {{
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_md']};
        }}
        QLabel#SystemGlyph {{
            color: {t['accent']};
            font-size: {t.get('subtitle_size', '12px')};
            font-weight: 800;
            background: {t['accent_light']};
            border: 1px solid {t['sidebar_active_border']};
            border-radius: {t['radius_sm']};
            padding: 6px 8px;
        }}
        QLabel#SystemStatusTitle {{
            font-weight: 600;
            font-size: {t.get('section_title_size', '15px')};
            color: {t['accent']};
        }}
        QLabel#SystemStatusDesc {{
            color: {t['fg_secondary']};
            font-size: {t.get('subtitle_size', '12px')};
        }}
        QLabel#InfoTip {{
            color: {t['fg_secondary']};
            padding: 14px 16px;
            background: {t['card_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_sm']};
            font-size: {t.get('subtitle_size', '12px')};
        }}
        QFrame#KeyInfoPanel QLabel#InfoTip {{
            padding: 0;
            background: transparent;
            border: none;
        }}
        QFrame#KeyPairListRow {{
            background: transparent;
            border: none;
        }}
        QLabel#KeyPairName {{
            color: {t['fg']};
            font-size: {t.get('label_size', '13px')};
            font-weight: 800;
        }}
        QLabel#KeyPairMeta {{
            color: {t['fg_secondary']};
            font-size: {t.get('caption_size', '11px')};
            font-weight: 500;
        }}
        QLabel#KeyPairStatus {{
            border-radius: {t.get('radius_pill', '9px')};  /* 状态药丸半圆端,走 token */
            padding: 4px 9px;
            font-size: {t.get('caption_size', '11px')};
            font-weight: 800;
        }}
        QLabel#KeyPairStatus[state="ready"] {{
            color: {t['success']};
            background: {t['success_light']};
            border: 1px solid rgba(52, 199, 89, 0.22);
        }}
        QLabel#KeyPairStatus[state="warning"] {{
            color: {t['warning']};
            background: rgba(255, 159, 10, 0.12);
            border: 1px solid rgba(255, 159, 10, 0.24);
        }}

        QTextEdit#LogTextEdit {{
            background: {t['list_bg']};
            border: 1px solid {t['glass_border_subtle']};
            border-radius: {t['radius_md']};
            padding: 12px;
            font-family: {get_monospace_font_qss()};
            font-size: {t.get('subtitle_size', '12px')};
        }}
        """
        self.setStyleSheet(qss)
        # 侧栏半透明 sidebar 色(0.84/0.92)透出的是衬底 MainSurface 的 bg。切主题时若只
        # 重画 sidebar 自身半透明层、不管衬底，sidebar 会透出 MainSurface 残留的旧主题
        # 深色 → 切回白天残留黑夜底色，侧栏整体“发暗/发灰”。故须按“衬底→半透明→子件”
        # 顺序强制重绘整条：顶层 QMainWindow → MainSurface(真正衬底) → 半透明 Sidebar。
        # 衬底先清成新主题 bg，半透明 sidebar 叠在新干净衬底上才不透出旧 Dark 色。
        self.repaint()
        self.main_surface.repaint()
        self.sidebar.repaint()

        for btn in self.all_buttons:
            btn.update_theme(t)

        for btn in self.sidebar_btns:
            btn.update()

        for badge in self.findChildren(IconBadge):
            badge.update()

        self.content_stack.update()

        self.ui_enc["list"].update_theme(t)
        self.ui_dec["list"].update_theme(t)

        # 主题喂给 CustomCheckBox，使其 paintEvent 直接读缓存、免每帧 import/链查（R3）。
        for ui in (self.ui_enc, self.ui_dec):
            for key in ("chk_struct", "chk_dir_name_enc", "chk_ssd", "chk_name", "chk_del"):
                chk = ui.get(key)
                if chk is not None:
                    chk.update_theme(t)

        if "scroll_area" in self.ui_enc:
            self.ui_enc["scroll_area"].update_theme(t)
        if "scroll_area" in self.ui_dec:
            self.ui_dec["scroll_area"].update_theme(t)

    # ================= 逻辑控制 =================
    def update_queue_count(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        panel = ui.get("queue_panel")
        if panel:
            panel.set_count(ui["list"].count())

    def check_constraints(self):
        for ui in (self.ui_enc, self.ui_dec):
            ui["txt_ssd"].setEnabled(not self.use_new_system)
            ui["btn_ssd"].setEnabled(not self.use_new_system)
            ui["btn_ssd_reset"].setEnabled(bool(self.custom_ssd_path) and not self.use_new_system)

        self.ui_enc["btn_path_reset"].setEnabled(bool(self.custom_enc_path))
        self.ui_dec["btn_path_reset"].setEnabled(bool(self.custom_dec_path))

        # 1. 输出路径 -> 保留目录结构
        enc_path = self.custom_enc_path
        if self.use_new_system:
            self.ui_enc["chk_struct"].setChecked(False)
            self.ui_enc["chk_struct"].setEnabled(False)
            self.ui_enc["chk_dir_name_enc"].setChecked(False)
            self.ui_enc["chk_dir_name_enc"].setEnabled(False)
            self.ui_enc["chk_ssd"].setChecked(False)
            self.ui_enc["chk_ssd"].setEnabled(False)
        elif not enc_path:
            self.ui_enc["chk_struct"].setChecked(False)
            self.ui_enc["chk_struct"].setEnabled(False)
        else:
            self.ui_enc["chk_struct"].setEnabled(True)
            self.ui_enc["chk_dir_name_enc"].setEnabled(self.ui_enc["chk_struct"].isChecked())

        dec_path = self.custom_dec_path
        if self.use_new_system:
            self.ui_dec["chk_struct"].setChecked(False)
            self.ui_dec["chk_struct"].setEnabled(False)
            self.ui_dec["chk_dir_name_enc"].setChecked(False)
            self.ui_dec["chk_dir_name_enc"].setEnabled(False)
            self.ui_dec["chk_ssd"].setChecked(False)
            self.ui_dec["chk_ssd"].setEnabled(False)
        elif not dec_path:
            self.ui_dec["chk_struct"].setChecked(False)
            self.ui_dec["chk_struct"].setEnabled(False)
        else:
            self.ui_dec["chk_struct"].setEnabled(True)
            self.ui_dec["chk_dir_name_enc"].setEnabled(self.ui_dec["chk_struct"].isChecked())

        # 2. SSD 路径 -> 启用 SSD 加速
        if self.use_new_system:
            return
        if self.custom_ssd_path:
            self.ui_enc["chk_ssd"].setEnabled(True)
            self.ui_dec["chk_ssd"].setEnabled(True)
        else:
            self.ui_enc["chk_ssd"].setChecked(False)
            self.ui_enc["chk_ssd"].setEnabled(False)
            self.ui_dec["chk_ssd"].setChecked(False)
            self.ui_dec["chk_ssd"].setEnabled(False)

    def _set_task_setup_enabled(self, is_encrypt, enabled):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        control_names = (
            "list", "pwd", "path", "txt_ssd", "combo_key", "txt_key_pwd",
            "chk_name", "chk_del", "chk_struct", "chk_dir_name_enc", "chk_ssd",
            "btn_add", "btn_add_folder", "btn_del", "btn_clr",
            "btn_path", "btn_path_reset", "btn_ssd", "btn_ssd_reset", "btn_run",
        )
        for name in control_names:
            widget = ui.get(name)
            if widget is not None:
                widget.setEnabled(enabled)

        if enabled:
            self.check_constraints()
        else:
            ui["chk_struct"].setEnabled(False)
            ui["chk_dir_name_enc"].setEnabled(False)
            ui["chk_ssd"].setEnabled(False)

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
            self.update_queue_count(is_encrypt)
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
                self.update_queue_count(is_encrypt)
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
            self.update_queue_count(is_encrypt)
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

    def action_clear_dir(self, is_encrypt):
        if is_encrypt:
            self.custom_enc_path = None
            self.ui_enc["path"].clear()
            self.ui_enc["chk_struct"].setChecked(False)
            self.append_log("加密输出目录已恢复为默认")
        else:
            self.custom_dec_path = None
            self.ui_dec["path"].clear()
            self.ui_dec["chk_struct"].setChecked(False)
            self.append_log("解密输出目录已恢复为默认")
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

    def action_clear_ssd(self):
        self.custom_ssd_path = None
        self.ui_enc["txt_ssd"].clear()
        self.ui_dec["txt_ssd"].clear()
        self.ui_enc["chk_ssd"].setChecked(False)
        self.ui_dec["chk_ssd"].setChecked(False)
        self.append_log("SSD 缓存路径已清除")
        self.check_constraints()

    def reset_ui_state(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        ui["stack"].setCurrentIndex(0)
        ui["pbar"].reset()  # 重置进度条并停止动画
        ui["status"].setText("就绪")
        ui["btn_pause"].setText("挂起")
        ui["btn_pause"].set_icon_name("pause")
        ui["delete_confirmed"] = False
        self._set_task_setup_enabled(is_encrypt, True)
        self.update_queue_count(is_encrypt)
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

            if not self._confirm_destructive_cleanup(files, is_encrypt, ui):
                return
            sys_logger.log(f"[新系统] 使用密钥: {key_name}")
            self._start_new_system_process(is_encrypt, files, path, key_path, key_pwd, ui)
        else:
            pwd = ui["pwd"].text()
            if not pwd:
                return QMessageBox.warning(self, "安全提示", "必须输入密码。")
            if not self._confirm_destructive_cleanup(files, is_encrypt, ui):
                return
            self._start_old_system_process(is_encrypt, files, path, pwd, ui)

    def _confirm_destructive_cleanup(self, files, is_encrypt, ui):
        ui["delete_confirmed"] = False
        chk_del = ui.get("chk_del")
        if not chk_del or not chk_del.isChecked():
            return True

        target_name = "源文件" if is_encrypt else "加密包"
        preview_limit = 8
        preview = "\n".join(files[:preview_limit])
        if len(files) > preview_limit:
            preview += f"\n... 以及另外 {len(files) - preview_limit} 个文件"

        reply = QMessageBox.warning(
            self,
            "二次确认删除",
            f"你已开启“完成后删除{target_name}”。\n\n"
            f"任务成功处理后，将删除队列中的对应{target_name}：\n{preview}\n\n"
            "此操作不可撤销，是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False
        ui["delete_confirmed"] = True
        return True

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

        self._set_task_setup_enabled(is_encrypt, False)
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
        task_type = "加密" if is_encrypt else "解密"
        sys_logger.log(f"========== [新系统] 开始{task_type}任务 ==========")
        sys_logger.log(f"文件数量: {len(files)}")
        sys_logger.log(f"密钥: {os.path.basename(key_path)}")
        sys_logger.log(f"输出目录: {path if path else '原地覆盖'}")

        self._set_task_setup_enabled(is_encrypt, False)
        ui["stack"].setCurrentIndex(1)
        ui["pbar"].setValue(0)
        ui["pbar"].start_shimmer()  # 启动流光动画
        ui["status"].setText("初始化引擎...")

        self.is_paused = False
        self.worker = RSABatchWorkerThread(
            files, is_encrypt, key_path, key_pwd,
            custom_out_dir=path,
            encrypt_filename=ui["chk_name"].isChecked() if is_encrypt and ui["chk_name"] else False
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
            ui["btn_pause"].set_icon_name("pause")
            ui["status"].setText("正在处理...")
        else:
            self.worker.pause()
            self.is_paused = True
            ui["btn_pause"].setText("继续")
            ui["btn_pause"].set_icon_name("play")
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
        self._set_task_setup_enabled(is_encrypt, True)
        ui["list"].clear()
        self.update_queue_count(is_encrypt)

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
        if chk_del.isChecked() and ui.get("delete_confirmed"):
            self.append_log("执行安全删除...")
            sys_logger.log("开始删除源文件...")
            for src, _ in results["success"]:
                try:
                    os.remove(src)
                    sys_logger.log(f"已删除: {src}")
                except Exception as e:
                    sys_logger.log(f"删除失败: {src}, 错误: {e}")
        ui["delete_confirmed"] = False

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
        self.key_list_header.setVisible(self.use_new_system)
        self.key_list.setVisible(self.use_new_system)
        self.btn_delete_key.setVisible(self.use_new_system)
        self.btn_refresh_keys.setVisible(self.use_new_system)
        if self.use_new_system:
            self.key_page_bottom_spacer.changeSize(0, 0, QSizePolicy.Minimum, QSizePolicy.Fixed)
        else:
            self.key_page_bottom_spacer.changeSize(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.key_page_layout.invalidate()

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
                item = QListWidgetItem()
                item.setData(Qt.UserRole, key_name)
                item.setSizeHint(QSize(0, 68))
                row = KeyPairListRow(key_name, files['public'], files['private'])
                self.key_list.addItem(item)
                self.key_list.setItemWidget(item, row)

            sys_logger.log(f"[新系统] 刷新密钥列表，共 {len(key_pairs)} 个密钥对")
        else:
            sys_logger.log(f"[老系统] 无需密钥管理")

    def action_switch_system(self):
        self.use_new_system = not self.use_new_system
        self.btn_switch_system.set_new_system(self.use_new_system)  # 使用新方法设置状态
        if self.use_new_system:
            self.lbl_system_status.setText("新加密系统")
            self.lbl_system_desc.setText("非对称加密 (RSA-2048)")
            if hasattr(self, 'system_icon_badge'):
                self.system_icon_badge.set_icon("rsa")
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
            if hasattr(self, 'system_icon_badge'):
                self.system_icon_badge.set_icon("key")
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
        self.check_constraints()
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
            self.refresh_key_combos()

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
        self.refresh_key_combos()
        dialog.accept()
        QMessageBox.information(self, "完成", "密钥对导入成功！")

    def action_delete_key(self):
        if not self.use_new_system:
            return QMessageBox.information(self, "提示", "老系统无需管理密钥")

        selected = self.key_list.currentItem()
        if not selected:
            return QMessageBox.warning(self, "提示", "请先选择要删除的密钥对")

        key_name = selected.data(Qt.UserRole)
        if not key_name:
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
                self.refresh_key_combos()
                QMessageBox.information(self, "完成", "密钥对已删除")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
