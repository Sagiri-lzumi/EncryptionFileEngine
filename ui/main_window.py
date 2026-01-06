import os
import time
import threading
import hashlib
import multiprocessing
import shutil
import base64
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QAbstractItemView,
                               QFrame, QStackedWidget, QApplication, QCheckBox)
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPainter, QColor

from config import DIRS
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger

# 尝试导入 Splash，如无则忽略
try:
    from ui.splash import IntroScreen
except ImportError:
    pass

# ================= 样式表 =================
DARK_THEME = """
QMainWindow, QWidget { background-color: #1c1c1e; color: #ffffff; font-family: 'Segoe UI', 'Microsoft YaHei'; font-size: 10pt; }
QFrame#TopBar { background-color: rgba(44, 44, 46, 0.8); border-bottom: 1px solid rgba(84, 84, 88, 0.6); }
QGroupBox { border: none; border-radius: 12px; margin-top: 28px; background-color: #2c2c2e; padding-top: 20px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; color: #8e8e93; font-weight: 600; }
QListWidget { background-color: rgba(0, 0, 0, 0.2); border-radius: 10px; padding: 5px; }
QListWidget::item { height: 36px; padding-left: 10px; color: #dddddd; }
QListWidget::item:selected { background-color: #0a84ff; color: #ffffff; }
QLineEdit, QTextEdit { background-color: rgba(0, 0, 0, 0.2); border-radius: 8px; color: #ffffff; padding: 8px; }
QPushButton { background-color: rgba(255, 255, 255, 0.08); color: #ffffff; border-radius: 8px; padding: 8px 16px; }
QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); }
QPushButton[class="primary"] { background-color: #0a84ff; font-weight: 600; }
QPushButton[class="primary"]:hover { background-color: #0077ed; }
QPushButton[class="danger"] { background-color: rgba(255, 69, 58, 0.15); color: #ff453a; }
QPushButton[class="danger"]:hover { background-color: #ff453a; color: #ffffff; }
QProgressBar { background-color: rgba(255, 255, 255, 0.1); border: none; height: 6px; border-radius: 3px; }
QProgressBar::chunk { background-color: #0a84ff; border-radius: 3px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: #8e8e93; padding: 10px 20px; font-weight: 600; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #0a84ff; border-bottom: 2px solid #0a84ff; }
QCheckBox { color: #cccccc; spacing: 8px; }
QCheckBox:disabled { color: #555555; }
"""

LIGHT_THEME = """
QMainWindow, QWidget { background-color: #f2f2f7; color: #000000; font-family: 'Segoe UI', 'Microsoft YaHei'; font-size: 10pt; }
QFrame#TopBar { background-color: rgba(255, 255, 255, 0.7); border-bottom: 1px solid rgba(0, 0, 0, 0.05); }
QGroupBox { border: 1px solid rgba(0,0,0,0.03); border-radius: 12px; margin-top: 28px; background-color: #ffffff; padding-top: 20px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; color: #8e8e93; font-weight: 600; }
QListWidget { background-color: #f2f2f7; border-radius: 10px; padding: 5px; }
QListWidget::item { height: 36px; padding-left: 10px; color: #1c1c1e; }
QListWidget::item:selected { background-color: #007aff; color: #ffffff; }
QLineEdit, QTextEdit { background-color: #f2f2f7; border-radius: 8px; color: #1c1c1e; padding: 8px; }
QPushButton { background-color: #ffffff; color: #000000; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 8px 16px; }
QPushButton:hover { background-color: #f9f9f9; }
QPushButton[class="primary"] { background-color: #007aff; color: #ffffff; border: none; font-weight: 600; }
QPushButton[class="primary"]:hover { background-color: #006bd6; }
QPushButton[class="danger"] { background-color: #fff2f2; color: #ff3b30; border: 1px solid #ffcccc; }
QPushButton[class="danger"]:hover { background-color: #ff3b30; color: #ffffff; }
QProgressBar { background-color: #e5e5ea; border: none; height: 6px; border-radius: 3px; }
QProgressBar::chunk { background-color: #007aff; border-radius: 3px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: #8e8e93; padding: 10px 20px; font-weight: 600; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #007aff; border-bottom: 2px solid #007aff; }
QCheckBox { color: #333333; spacing: 8px; }
QCheckBox:disabled { color: #aaaaaa; }
"""


# ================= 组件：拖拽列表 =================
class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.theme_mode = "dark"

    def dragEnterEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dragMoveEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            added = False
            existing_files = set()
            for i in range(self.count()):
                existing_files.add(self.item(i).text())

            for url in e.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path):
                    if path not in existing_files:
                        self.addItem(path)
                        existing_files.add(path)
                        added = True
                elif os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            full_path = os.path.normpath(full_path)
                            if full_path not in existing_files:
                                self.addItem(full_path)
                                existing_files.add(full_path)
                                added = True

            if added and self.window():
                try:
                    # 触发约束检查
                    self.window().check_constraints()
                    self.window().reset_ui_state(self.window().tabs.currentIndex() == 0)
                except:
                    pass

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.save()
            color = QColor("#666666") if self.theme_mode == "dark" else QColor("#999999")
            painter.setPen(color)
            font = self.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, "请将文件或文件夹拖入此区域")
            painter.restore()


# ================= 辅助函数与常量 =================

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
    """获取路径所在的驱动器根目录"""
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        parent = os.path.dirname(path)
        if parent == path:
            return parent
        path = parent
    return path


def encrypt_dir_name_str(dir_name):
    """加密文件夹名：添加前缀并Base64"""
    try:
        # 避免重复加密
        if dir_name.startswith(ENC_PREFIX): return dir_name
        encoded = base64.urlsafe_b64encode(dir_name.encode()).decode()
        return f"{ENC_PREFIX}{encoded}"
    except:
        return dir_name


def decrypt_dir_name_str(dir_name):
    """【智能检测】只有当文件夹名包含特征前缀时才解密"""
    if dir_name.startswith(ENC_PREFIX):
        try:
            encoded = dir_name[len(ENC_PREFIX):]
            return base64.urlsafe_b64decode(encoded.encode()).decode()
        except:
            return dir_name
    # 否则原样返回
    return dir_name


# ================= 跨进程任务 Wrapper =================
def task_wrapper(file_path, target_full_path, key_bytes, is_enc, enc_name, queue, stop_event, pause_event):
    """
    进程池任务：直接调用 Engine 将 file_path 处理到 target_full_path。
    """
    from core.file_cipher import FileCipherEngine
    import time

    class MPController:
        def is_stop_requested(self):
            return stop_event.is_set()

        def wait_if_paused(self):
            pause_event.wait()

    last_update = 0

    def mp_callback(current, total):
        nonlocal last_update
        now = time.time()
        # 减少 IPC 通信频率，每 0.05s 发送一次
        if now - last_update > 0.05 or current == total:
            queue.put(("PROGRESS", file_path, current, total))
            last_update = now

    engine = FileCipherEngine()
    try:
        # 发送开始信号
        queue.put(("START", file_path, os.path.getsize(file_path)))

        # 调用核心处理函数 process_file_direct
        success, msg, out_path = engine.process_file_direct(
            file_path, target_full_path, key_bytes, is_enc,
            encrypt_filename=enc_name,
            callback=mp_callback,
            controller=MPController()
        )
        return (file_path, success, msg, out_path)
    except Exception as e:
        # 捕获异常转为失败消息
        return (file_path, False, str(e), "")


# ================= 核心工作线程 =================
class BatchWorkerThread(QThread):
    sig_progress = Signal(str, int)
    sig_log = Signal(str)
    sig_finished = Signal(dict)

    def __init__(self, files, key, is_encrypt, encrypt_filename=False,
                 custom_out_dir=None,
                 keep_structure=False, encrypt_dirname=False,
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
        # 1. 预计算密钥字节流 (SHA256)
        key_bytes = hashlib.sha256(self.key.encode()).digest()

        results = {"success": [], "fail": []}

        # 2. 扫描与计算总大小
        valid_files = []
        total_bytes = 0
        self.processed_bytes_map = {}

        # 计算公共基准路径
        common_base = ""
        if self.keep_structure and len(self.files) > 0:
            try:
                common_base = os.path.commonpath(self.files)
                if os.path.isfile(common_base): common_base = os.path.dirname(common_base)
            except:
                pass

        self.sig_log.emit("--- 正在扫描任务队列 ---")
        for f in self.files:
            if os.path.exists(f):
                s = os.path.getsize(f)
                total_bytes += s
                valid_files.append(f)
                self.processed_bytes_map[f] = 0
            else:
                results["fail"].append((f, "文件不存在"))

        if not valid_files:
            self.sig_finished.emit(results)
            return

        # 3. SSD 空间检测 & 路径规划
        temp_stage_root = None
        working_root_base = None  # 实际写入的根目录

        if self.use_ssd and self.ssd_dir:
            try:
                # 获取分区根目录，创建临时暂存区
                drive_root = get_drive_root(self.ssd_dir)
                temp_stage_root = os.path.join(drive_root, "_SSD_ENCRYPT_STAGE_TEMP")

                # 【检测】SSD 空间是否足够 (预留 1.2 倍)
                usage = shutil.disk_usage(self.ssd_dir)
                required = total_bytes * 1.2

                if usage.free < required:
                    self.sig_log.emit(
                        f"⚠️ [空间检测] SSD 剩余空间不足! 需 {format_size(required)}, 余 {format_size(usage.free)}")
                    self.sig_log.emit("⚠️ 已自动降级为直接写入模式")
                    self.use_ssd = False
                    working_root_base = self.custom_out  # 降级后直接写目标
                else:
                    self.sig_log.emit(f"✅ [SSD 加速] 已启用。暂存区: {temp_stage_root}")
                    # 清理并重建暂存区
                    if os.path.exists(temp_stage_root): shutil.rmtree(temp_stage_root, ignore_errors=True)
                    os.makedirs(temp_stage_root, exist_ok=True)
                    working_root_base = temp_stage_root

            except Exception as e:
                self.sig_log.emit(f"❌ SSD 检测出错: {e}, 已禁用加速")
                self.use_ssd = False
                working_root_base = self.custom_out
        else:
            working_root_base = self.custom_out

        # 4. 任务分发
        max_workers = min(os.cpu_count(), len(valid_files))
        # 如果是 SSD，IO 吞吐大，可以多开几个线程
        if self.use_ssd: max_workers = max(max_workers, 4)

        self.sig_log.emit(f"🚀 启动 {max_workers} 个加密核心...")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for f_path in valid_files:
                # --- A. 确定该文件的输出基准目录 ---
                if not self.use_ssd and not self.custom_out:
                    current_base = os.path.dirname(f_path)
                else:
                    current_base = working_root_base

                # --- B. 计算相对结构 (智能解密检测在这里发生) ---
                rel_path_struct = ""
                if self.keep_structure and common_base:
                    try:
                        rel = os.path.relpath(os.path.dirname(f_path), common_base)
                        if rel == ".": rel = ""

                        # 处理每一层文件夹名
                        parts = rel.split(os.sep)
                        processed_parts = []
                        for p in parts:
                            if not p: continue
                            if self.is_enc:
                                # 加密模式：根据勾选决定是否加密目录名
                                if self.encrypt_dirname:
                                    processed_parts.append(encrypt_dir_name_str(p))
                                else:
                                    processed_parts.append(p)
                            else:
                                # 【解密模式】恢复自动检测逻辑
                                processed_parts.append(decrypt_dir_name_str(p))

                        rel_path_struct = os.sep.join(processed_parts)
                    except:
                        rel_path_struct = ""

                # --- C. 组合完整输出路径 ---
                final_out_dir = os.path.join(current_base, rel_path_struct)

                # 确定文件名
                fname = os.path.basename(f_path)
                if self.is_enc:
                    target_file_path = os.path.join(final_out_dir, fname + ".enc")
                else:
                    # 解密时可以去掉 .enc，也可以保留原名由 FileCipher 覆盖
                    target_file_path = os.path.join(final_out_dir, fname)

                # 提交任务
                futures.append(executor.submit(
                    task_wrapper,
                    f_path, target_file_path, key_bytes, self.is_enc, self.enc_name,
                    self.queue, self.stop_event, self.pause_event
                ))

            # 5. 进度监听
            finished_count = 0
            # SSD 模式下，加密占 60% 进度，移动占 40%
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

            if not self._is_running:
                executor.shutdown(wait=False, cancel_futures=True)

        # 6. SSD 模式收尾：统一剪切
        if self.use_ssd and self._is_running and temp_stage_root:
            self.sig_log.emit("--- ⚡ SSD 高速回写 (统一剪切) ---")

            try:
                final_dest_root = self.custom_out
                # 如果没有自定义输出目录，回写到 common_base 或源文件所在目录
                if not final_dest_root:
                    final_dest_root = common_base if common_base else os.path.dirname(self.files[0])

                if not os.path.exists(final_dest_root):
                    os.makedirs(final_dest_root, exist_ok=True)

                items = os.listdir(temp_stage_root)
                total_items = len(items)
                moved_c = 0

                for item in items:
                    src_item = os.path.join(temp_stage_root, item)
                    dst_item = os.path.join(final_dest_root, item)

                    if os.path.exists(dst_item):
                        if os.path.isdir(dst_item):
                            shutil.rmtree(dst_item)
                        else:
                            os.remove(dst_item)

                    shutil.move(src_item, dst_item)

                    moved_c += 1
                    pct = 60 + int((moved_c / total_items) * 40)
                    self.sig_progress.emit(f"回写数据... {pct}%", pct)

                shutil.rmtree(temp_stage_root)
                self.sig_log.emit("✅ 回写完成，缓存已清理")

            except Exception as e:
                self.sig_log.emit(f"❌ 回写失败: {e} | 数据保留在: {temp_stage_root}")

        msg = "任务完成" if self._is_running else "已终止"
        self.sig_progress.emit(msg, 100)
        self.sig_finished.emit(results)


# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Security Engine Enterprise")
        self.resize(1100, 800)
        self.setMinimumSize(950, 680)

        self.is_dark = False
        self.custom_enc_path = None
        self.custom_dec_path = None
        self.custom_ssd_path = None
        self.last_out_dir = ""
        self.is_paused = False
        self.worker = None

        self._init_ui()
        self.apply_theme()

    def _init_ui(self):
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部栏
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(64)
        self.top_bar.setObjectName("TopBar")
        hl = QHBoxLayout(self.top_bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(20)
        self.lbl_title = QLabel("安全加密引擎内核")
        self.lbl_title.setStyleSheet(
            "font-family: 'Segoe UI', 'Microsoft YaHei'; font-weight: 600; font-size: 13pt; letter-spacing: 1px;")
        hl.addWidget(self.lbl_title)
        hl.addStretch()
        self.btn_theme = QPushButton("外观模式")
        self.btn_theme.setFixedSize(100, 36)
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)
        hl.addWidget(self.btn_theme)
        main_layout.addWidget(self.top_bar)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self._init_tab_encrypt()
        self._init_tab_decrypt()
        self._init_tab_log()

        # 初始化时检查一次约束
        self.check_constraints()

    def _create_common_layout(self, is_encrypt):
        page = QWidget()
        h_layout = QHBoxLayout(page)
        h_layout.setContentsMargins(25, 25, 25, 25)
        h_layout.setSpacing(25)

        # 左侧列表
        grp_left = QGroupBox("文件处理队列")
        v_left = QVBoxLayout(grp_left)
        file_list = DragDropListWidget()
        file_list.theme_mode = "dark" if self.is_dark else "light"
        btn_bar = QHBoxLayout()
        btn_add = QPushButton("添加文件...")
        btn_add.clicked.connect(lambda: self.action_add_file(is_encrypt))
        btn_del = QPushButton("移除选中项")
        btn_del.clicked.connect(lambda: self.action_remove_file(file_list, is_encrypt))
        btn_clr = QPushButton("清空队列")
        btn_clr.clicked.connect(lambda: (file_list.clear(), self.reset_ui_state(is_encrypt)))
        btn_bar.addWidget(btn_add);
        btn_bar.addWidget(btn_del);
        btn_bar.addWidget(btn_clr)
        v_left.addWidget(file_list);
        v_left.addLayout(btn_bar)

        # 右侧配置
        grp_right = QGroupBox("执行参数配置")
        grp_right.setFixedWidth(400)
        v_right = QVBoxLayout(grp_right)
        v_right.setSpacing(12)

        v_right.addWidget(QLabel("安全密钥:"))
        txt_pwd = QLineEdit()
        txt_pwd.setEchoMode(QLineEdit.Password)
        txt_pwd.setPlaceholderText("请输入加密/解密专用密钥")
        txt_pwd.setMinimumHeight(38)
        v_right.addWidget(txt_pwd)

        v_right.addWidget(QLabel("输出路径:"))
        h_path = QHBoxLayout()
        txt_path = QLineEdit()
        txt_path.setPlaceholderText("留空则默认覆盖源目录 (原地操作)")
        txt_path.setReadOnly(True)
        btn_path = QPushButton("浏览...")
        btn_path.setFixedWidth(80)
        btn_path.clicked.connect(lambda: self.action_select_dir(is_encrypt))
        h_path.addWidget(txt_path);
        h_path.addWidget(btn_path)
        v_right.addLayout(h_path)

        # --- [修改] 目录结构选项 ---
        chk_struct = QCheckBox("保留目录层级结构")
        chk_dir_name_enc = QCheckBox("解密文件夹名称（按需选）")
        chk_dir_name_enc.setEnabled(False)

        def on_struct_toggled(state):
            is_checked = (state == 2)
            chk_dir_name_enc.setEnabled(is_checked)
            if not is_checked:
                chk_dir_name_enc.setChecked(False)

        chk_struct.stateChanged.connect(on_struct_toggled)

        v_right.addWidget(chk_struct)
        v_right.addWidget(chk_dir_name_enc)

        line = QFrame();
        line.setFrameShape(QFrame.HLine);
        line.setFrameShadow(QFrame.Sunken)
        v_right.addWidget(line)

        # --- SSD 加速 ---
        chk_ssd = QCheckBox("启用 SSD 固态硬盘缓存加速")
        h_ssd = QHBoxLayout()
        # 兼容 config 可能没有 TEMP 的情况
        temp_dir = DIRS["TEMP"] if "TEMP" in DIRS else ""
        txt_ssd = QLineEdit(temp_dir)
        txt_ssd.setReadOnly(True)
        txt_ssd.setEnabled(False)
        btn_ssd = QPushButton("择盘")
        btn_ssd.setFixedWidth(80)
        btn_ssd.setEnabled(False)

        def on_ssd_toggled(state):
            is_checked = (state == 2)
            txt_ssd.setEnabled(is_checked)
            btn_ssd.setEnabled(is_checked)
            if is_checked and not self.custom_ssd_path and "TEMP" in DIRS:
                self.custom_ssd_path = DIRS["TEMP"]

        chk_ssd.stateChanged.connect(on_ssd_toggled)
        btn_ssd.clicked.connect(lambda: self.action_select_ssd(is_encrypt))

        h_ssd.addWidget(txt_ssd);
        h_ssd.addWidget(btn_ssd)
        v_right.addWidget(chk_ssd)
        v_right.addLayout(h_ssd)

        line2 = QFrame();
        line2.setFrameShape(QFrame.HLine);
        line2.setFrameShadow(QFrame.Sunken)
        v_right.addWidget(line2)

        # 常规选项
        chk_name = None
        chk_del = None
        if is_encrypt:
            chk_name = QCheckBox("加密文件名")
            chk_name.setChecked(True)
            chk_del = QCheckBox("操作完成后删除源文件")
            v_right.addWidget(chk_name)
            v_right.addWidget(chk_del)
        else:
            chk_del = QCheckBox("解密后移除加密包")
            v_right.addWidget(chk_del)

        v_right.addStretch()

        lbl_status = QLabel("等待指令")
        lbl_status.setAlignment(Qt.AlignCenter)
        lbl_status.setStyleSheet("color: #888; font-weight: bold;")
        pbar = QProgressBar()
        pbar.setValue(0)
        pbar.setFormat("%p%")

        v_right.addWidget(lbl_status)
        v_right.addWidget(pbar)
        v_right.addSpacing(10)

        stack = QStackedWidget()

        w_start = QWidget();
        l_start = QVBoxLayout(w_start);
        l_start.setContentsMargins(0, 0, 0, 0)
        btn_run = QPushButton(f"执行{'加密' if is_encrypt else '解密'}程序")
        btn_run.setProperty("class", "primary")
        btn_run.setMinimumHeight(48)
        btn_run.clicked.connect(self.run_encrypt if is_encrypt else self.run_decrypt)
        l_start.addWidget(btn_run)
        stack.addWidget(w_start)

        w_ctrl = QWidget();
        l_ctrl = QHBoxLayout(w_ctrl);
        l_ctrl.setContentsMargins(0, 0, 0, 0);
        l_ctrl.setSpacing(10)
        btn_pause = QPushButton("挂起任务");
        btn_pause.setMinimumHeight(48);
        btn_pause.clicked.connect(self.action_toggle_pause)
        btn_stop = QPushButton("终止操作");
        btn_stop.setProperty("class", "danger");
        btn_stop.setMinimumHeight(48);
        btn_stop.clicked.connect(self.action_stop_task)
        l_ctrl.addWidget(btn_pause);
        l_ctrl.addWidget(btn_stop)
        stack.addWidget(w_ctrl)

        w_res = QWidget();
        l_res = QHBoxLayout(w_res);
        l_res.setContentsMargins(0, 0, 0, 0);
        l_res.setSpacing(10)
        btn_open = QPushButton("打开输出目录");
        btn_open.setMinimumHeight(48);
        btn_open.clicked.connect(self.action_open_folder)
        btn_back = QPushButton("返回继续工作");
        btn_back.setMinimumHeight(48);
        btn_back.clicked.connect(lambda: self.reset_ui_state(is_encrypt))
        l_res.addWidget(btn_open);
        l_res.addWidget(btn_back)
        stack.addWidget(w_res)

        v_right.addWidget(stack)

        h_layout.addWidget(grp_left, 6)
        h_layout.addWidget(grp_right, 4)

        refs = {
            "list": file_list, "pwd": txt_pwd, "path": txt_path,
            "chk_name": chk_name, "chk_del": chk_del,
            "chk_struct": chk_struct, "chk_dir_name_enc": chk_dir_name_enc,
            "chk_ssd": chk_ssd, "txt_ssd": txt_ssd,
            "status": lbl_status, "pbar": pbar, "stack": stack,
            "btn_pause": btn_pause
        }
        return page, refs

    def _init_tab_encrypt(self):
        page, refs = self._create_common_layout(True)
        self.ui_enc = refs
        self.tabs.addTab(page, "加密终端")

    def _init_tab_decrypt(self):
        page, refs = self._create_common_layout(False)
        self.ui_dec = refs
        self.tabs.addTab(page, "解密终端")

    def _init_tab_log(self):
        page = QWidget()
        vl = QVBoxLayout(page);
        vl.setContentsMargins(25, 25, 25, 25)
        grp = QGroupBox("系统运行日志");
        v = QVBoxLayout(grp)
        self.txt_log = QTextEdit();
        self.txt_log.setReadOnly(True)
        v.addWidget(self.txt_log);
        vl.addWidget(grp)
        self.tabs.addTab(page, "日志审计")

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(DARK_THEME if self.is_dark else LIGHT_THEME)
        bg = "#252526" if self.is_dark else "#f0f0f0"
        border = "#3e3e42" if self.is_dark else "#c0c0c0"
        self.top_bar.setStyleSheet(f"background-color: {bg}; border-bottom: 1px solid {border};")
        self.ui_enc["list"].theme_mode = "dark" if self.is_dark else "light"
        self.ui_dec["list"].theme_mode = "dark" if self.is_dark else "light"
        self.ui_enc["list"].viewport().update()
        self.ui_dec["list"].viewport().update()

    def check_constraints(self):
        """
        [新增] 约束检查：
        如果 输出目录 == 源目录 (即用户没选输出目录，path 为空)，
        则强制禁用并取消勾选 '保留目录层级'。
        """
        # 加密界面
        enc_path = self.custom_enc_path
        if not enc_path:  # 没选，默认为空，意味着原地
            self.ui_enc["chk_struct"].setChecked(False)
            self.ui_enc["chk_struct"].setEnabled(False)
            self.ui_enc["chk_struct"].setToolTip("原地输出不可保留目录层级，防止覆盖")

            # 【已修改】移除了强制关闭文件名的逻辑，即使原地加密，也允许用户勾选（默认已勾选）
        else:
            self.ui_enc["chk_struct"].setEnabled(True)
            self.ui_enc["chk_struct"].setToolTip("")
            if self.ui_enc["chk_name"]:
                self.ui_enc["chk_name"].setEnabled(True)

        # 解密界面同理 (虽然解密一般不需要chk_name，但chk_struct需要)
        dec_path = self.custom_dec_path
        if not dec_path:
            self.ui_dec["chk_struct"].setChecked(False)
            self.ui_dec["chk_struct"].setEnabled(False)
        else:
            self.ui_dec["chk_struct"].setEnabled(True)

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

    def action_remove_file(self, lst, is_encrypt):
        self.reset_ui_state(is_encrypt)
        for item in lst.selectedItems():
            lst.takeItem(lst.row(item))
        self.check_constraints()

    def action_select_dir(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            if is_encrypt:
                self.custom_enc_path = d;
                self.ui_enc["path"].setText(d)
            else:
                self.custom_dec_path = d;
                self.ui_dec["path"].setText(d)
        self.check_constraints()

    def action_select_ssd(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择 SSD 缓存目录")
        if d:
            self.custom_ssd_path = d
            ui = self.ui_enc if is_encrypt else self.ui_dec
            ui["txt_ssd"].setText(d)

    def reset_ui_state(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        ui["stack"].setCurrentIndex(0)
        ui["pbar"].setValue(0)
        ui["status"].setText("等待指令")
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
        if count == 0: return QMessageBox.warning(self, "操作提示", "任务队列为空。")
        pwd = ui["pwd"].text()
        if not pwd: return QMessageBox.warning(self, "安全提示", "必须输入密钥。")

        files = [ui["list"].item(i).text() for i in range(count)]
        path = self.custom_enc_path if is_encrypt else self.custom_dec_path

        # 获取选项状态
        keep_struct = ui["chk_struct"].isChecked()
        enc_dirname = ui["chk_dir_name_enc"].isEnabled() and ui["chk_dir_name_enc"].isChecked()
        use_ssd = ui["chk_ssd"].isChecked()
        ssd_path = self.custom_ssd_path if use_ssd else None

        if use_ssd and not ssd_path:
            if "TEMP" in DIRS:
                ssd_path = DIRS["TEMP"]

        ui["list"].setEnabled(False)
        ui["pwd"].setEnabled(False)
        ui["stack"].setCurrentIndex(1)
        ui["pbar"].setValue(0)
        ui["status"].setText("正在初始化加密引擎...")

        self.is_paused = False
        self.worker = BatchWorkerThread(
            files, pwd, is_encrypt,
            encrypt_filename=ui["chk_name"].isChecked() if is_encrypt and ui["chk_name"] else False,
            custom_out_dir=path,
            keep_structure=keep_struct,
            encrypt_dirname=enc_dirname,
            use_ssd=use_ssd,
            ssd_dir=ssd_path
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
        t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = "#a0a0a0" if self.is_dark else "#666"
        self.txt_log.append(f"<span style='color:{color}'>[{t}]</span> {text}")
        sys_logger.log(text)

    def action_toggle_pause(self):
        if not self.worker: return
        is_enc_task = self.worker.is_enc
        ui = self.ui_enc if is_enc_task else self.ui_dec
        if self.is_paused:
            self.worker.resume();
            self.is_paused = False
            ui["btn_pause"].setText("挂起任务");
            ui["status"].setText("正在处理...")
        else:
            self.worker.pause();
            self.is_paused = True
            ui["btn_pause"].setText("继续任务");
            ui["status"].setText("任务已挂起")

    def action_stop_task(self):
        if self.worker:
            if self.is_paused: self.worker.resume()
            self.worker.stop()
            self.append_log(f" 用户请求强行终止任务...")

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
            self.append_log("正在执行安全删除...")
            for src, _ in results["success"]:
                try:
                    os.remove(src);
                    self.append_log(f"已移除源文件: {os.path.basename(src)}")
                except Exception as e:
                    self.append_log(f"移除失败 {src}: {e}")

        succ = len(results["success"])
        fail = len(results["fail"])
        if fail == 0:
            QMessageBox.information(self, "操作完成", f"所有任务已成功执行。\n处理文件数: {succ}")
        else:
            QMessageBox.warning(self, "完成 (含异常)", f"成功: {succ}\n失败: {fail}\n请检查日志。")

    def action_open_folder(self):
        if self.last_out_dir and os.path.exists(self.last_out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out_dir))
        else:
            QMessageBox.information(self, "提示", "尚未生成输出目录。")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())