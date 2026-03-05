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
from ui.components import AnimatedSidebarButton, ModernButton, DragDropListWidget, CustomCheckBox, ThemeSelector
from ui.utils import ensure_long_path, format_size, get_drive_root


# ================= 辅助函数 =================
ENC_PREFIX = "ENC_DIR_"


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
        self.use_new_system = False  # False=老系统, True=新系统

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
        self.btn_nav_key = AnimatedSidebarButton("密钥管理", "🔑", self)
        self.btn_nav_log = AnimatedSidebarButton("日志审计", "📜", self)

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

        self.btn_theme = ModernButton("🎨 主题", "normal")
        self.btn_theme.clicked.connect(self.show_theme_selector)
        self.all_buttons.append(self.btn_theme)
        v_sidebar.addWidget(self.btn_theme)

        main_layout.addWidget(self.sidebar)

        # === 2. 右侧内容区 ===
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        self._init_page_encrypt()
        self._init_page_decrypt()
        self._init_page_key_management()
        self._init_page_log()

    def _init_tray(self):
        """初始化系统托盘"""
        # 设置图标
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fileenc.ico")
        if os.path.exists(icon_path):
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        else:
            self.tray_icon = QSystemTrayIcon(self)

        # 创建托盘菜单
        tray_menu = QMenu()

        # 显示主窗口
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        # 快捷功能
        encrypt_action = QAction("🔒 加密文件", self)
        encrypt_action.triggered.connect(lambda: self.show_and_switch(0))
        tray_menu.addAction(encrypt_action)

        decrypt_action = QAction("🔓 解密文件", self)
        decrypt_action.triggered.connect(lambda: self.show_and_switch(1))
        tray_menu.addAction(decrypt_action)

        log_action = QAction("📜 查看日志", self)
        log_action.triggered.connect(lambda: self.show_and_switch(2))
        tray_menu.addAction(log_action)

        tray_menu.addSeparator()

        # 退出
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

    def switch_page(self, index):
        """切换页面"""
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.sidebar_btns):
            btn.setChecked(i == index)
            btn.update()
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

        # 系统状态提示
        h_status = QHBoxLayout()
        if is_encrypt:
            self.lbl_enc_system = QLabel("🔹 老系统")
            self.lbl_enc_system.setStyleSheet("color: #5c6bc0; font-weight: bold;")
            h_status.addWidget(self.lbl_enc_system)
        else:
            self.lbl_dec_system = QLabel("🔹 老系统")
            self.lbl_dec_system.setStyleSheet("color: #5c6bc0; font-weight: bold;")
            h_status.addWidget(self.lbl_dec_system)
        h_status.addStretch()
        v_left.addLayout(h_status)

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

        # 老系统：密码输入
        self.old_sec_widget = QWidget() if is_encrypt else QWidget()
        v_old_sec = QVBoxLayout(self.old_sec_widget)
        v_old_sec.setContentsMargins(0, 0, 0, 0)
        txt_pwd = QLineEdit()
        txt_pwd.setEchoMode(QLineEdit.Password)
        txt_pwd.setPlaceholderText("输入密码...")
        v_old_sec.addWidget(txt_pwd)
        v_sec.addWidget(self.old_sec_widget)

        # 新系统：密钥选择
        self.new_sec_widget = QWidget() if is_encrypt else QWidget()
        v_new_sec = QVBoxLayout(self.new_sec_widget)
        v_new_sec.setContentsMargins(0, 0, 0, 0)

        if is_encrypt:
            lbl_key = QLabel("选择公钥:")
            lbl_key.setStyleSheet("color: #888; font-size: 10px;")
            v_new_sec.addWidget(lbl_key)
            combo_key = QComboBox()
            combo_key.setPlaceholderText("选择密钥对...")
            v_new_sec.addWidget(combo_key)
        else:
            lbl_key = QLabel("选择私钥:")
            lbl_key.setStyleSheet("color: #888; font-size: 10px;")
            v_new_sec.addWidget(lbl_key)
            combo_key = QComboBox()
            combo_key.setPlaceholderText("选择密钥对...")
            v_new_sec.addWidget(combo_key)
            txt_key_pwd = QLineEdit()
            txt_key_pwd.setEchoMode(QLineEdit.Password)
            txt_key_pwd.setPlaceholderText("私钥密码...")
            v_new_sec.addWidget(txt_key_pwd)

        v_sec.addWidget(self.new_sec_widget)
        self.new_sec_widget.hide()
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
        chk_struct = CustomCheckBox("保留目录结构")
        chk_struct.setEnabled(False)  # 默认禁用
        v_io.addWidget(chk_struct)

        chk_dir_name_enc = None
        if is_encrypt:
            # 逻辑：只有勾选了保留结构，才能勾选加密文件夹名
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
            # 解密时同理
            chk_dir_name_enc = CustomCheckBox("解密文件夹名")
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
        chk_ssd = CustomCheckBox("启用 SSD 加速")
        chk_ssd.setEnabled(False)  # 默认禁用
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

        v_right.addWidget(grp_adv)
        v_right.addStretch()

        # 状态与控制
        # 状态显示区域
        status_container = QFrame()
        status_container.setStyleSheet(f"background: {THEMES['Deep Space']['input_bg']}; border-radius: 8px; padding: 10px;")
        v_status = QVBoxLayout(status_container)
        v_status.setSpacing(8)

        lbl_status = QLabel("就绪")
        lbl_status.setAlignment(Qt.AlignCenter)
        lbl_status.setObjectName("StatusLabel")
        lbl_status.setFont(QFont("Segoe UI", 10, QFont.Bold))
        v_status.addWidget(lbl_status)

        pbar = QProgressBar()
        pbar.setValue(0)
        pbar.setTextVisible(True)
        pbar.setFormat("%p%")
        pbar.setFixedHeight(20)
        v_status.addWidget(pbar)

        v_right.addWidget(status_container)

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
            "btn_pause": btn_pause,
            "old_sec_widget": self.old_sec_widget,
            "new_sec_widget": self.new_sec_widget,
            "combo_key": combo_key,
            "txt_key_pwd": txt_key_pwd if not is_encrypt else None
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
        layout.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("ContentPanel")
        v = QVBoxLayout(container)
        v.setContentsMargins(30, 30, 30, 30)
        v.setSpacing(20)

        lbl = QLabel("🔑 密钥管理中心")
        lbl.setObjectName("SectionTitle")
        v.addWidget(lbl)

        # 系统切换卡片
        switch_card = QFrame()
        switch_card.setStyleSheet("background: rgba(92, 107, 192, 0.1); border-radius: 10px; padding: 15px;")
        h_switch = QHBoxLayout(switch_card)

        icon_lbl = QLabel("🔐")
        icon_lbl.setStyleSheet("font-size: 24px;")
        h_switch.addWidget(icon_lbl)

        v_status = QVBoxLayout()
        self.lbl_system_status = QLabel("老加密系统")
        self.lbl_system_status.setStyleSheet("font-weight: bold; font-size: 14px; color: #5c6bc0;")
        self.lbl_system_desc = QLabel("对称加密 (AES-256)")
        self.lbl_system_desc.setStyleSheet("color: #888; font-size: 11px;")
        v_status.addWidget(self.lbl_system_status)
        v_status.addWidget(self.lbl_system_desc)
        h_switch.addLayout(v_status)
        h_switch.addStretch()

        self.btn_switch_system = ModernButton("切换到新系统 →", "primary")
        self.btn_switch_system.setFixedWidth(150)
        self.btn_switch_system.clicked.connect(self.action_switch_system)
        self.all_buttons.append(self.btn_switch_system)
        h_switch.addWidget(self.btn_switch_system)
        v.addWidget(switch_card)

        # 密钥列表标题
        lbl_list = QLabel("📋 密钥列表")
        lbl_list.setStyleSheet("font-weight: bold; color: #5c6bc0; font-size: 12px; margin-top: 10px;")
        v.addWidget(lbl_list)

        self.key_list = QListWidget()
        self.key_list.setSelectionMode(QAbstractItemView.SingleSelection)
        v.addWidget(self.key_list)

        # 老系统提示
        self.old_system_widget = QWidget()
        v_old = QVBoxLayout(self.old_system_widget)
        v_old.setContentsMargins(0, 0, 0, 0)
        lbl_old_tip = QLabel("💡 老系统使用对称加密，加密时直接输入密码即可，无需预先生成密钥")
        lbl_old_tip.setStyleSheet("color: #888; font-style: italic; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 6px;")
        lbl_old_tip.setWordWrap(True)
        v_old.addWidget(lbl_old_tip)
        v.addWidget(self.old_system_widget)

        # 新系统输入框
        self.new_system_widget = QWidget()
        v_new = QVBoxLayout(self.new_system_widget)
        v_new.setContentsMargins(0, 0, 0, 0)
        v_new.setSpacing(10)

        lbl_new_tip = QLabel("🔐 生成新密钥对")
        lbl_new_tip.setStyleSheet("font-weight: bold; color: #5c6bc0; font-size: 11px;")
        v_new.addWidget(lbl_new_tip)

        h_new = QHBoxLayout()
        self.new_key_name_input = QLineEdit()
        self.new_key_name_input.setPlaceholderText("密钥对名称 (例如: my_key)")
        self.new_key_password_input = QLineEdit()
        self.new_key_password_input.setPlaceholderText("保护密码")
        self.new_key_password_input.setEchoMode(QLineEdit.Password)
        h_new.addWidget(self.new_key_name_input, 2)
        h_new.addWidget(self.new_key_password_input, 1)
        v_new.addLayout(h_new)
        v.addWidget(self.new_system_widget)
        self.new_system_widget.hide()

        # 按钮栏
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_gen_new = ModernButton("🔐 生成密钥对", "primary")
        self.btn_gen_new.clicked.connect(self.action_generate_keypair)
        self.all_buttons.append(self.btn_gen_new)
        self.btn_gen_new.hide()

        self.btn_import_new = ModernButton("📥 导入", "normal")
        self.btn_import_new.clicked.connect(self.action_import_keypair)
        self.all_buttons.append(self.btn_import_new)
        self.btn_import_new.hide()

        btn_delete = ModernButton("🗑️ 删除", "danger")
        btn_delete.clicked.connect(self.action_delete_key)
        self.all_buttons.append(btn_delete)

        btn_refresh = ModernButton("🔄 刷新", "normal")
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

    def show_theme_selector(self):
        """显示主题选择器"""
        btn_pos = self.btn_theme.mapToGlobal(QPoint(0, 0))
        popup_x = btn_pos.x()
        popup_y = btn_pos.y() - self.theme_selector.height() - 10
        self.theme_selector.show_at(QPoint(popup_x, popup_y))

    def on_theme_selected(self, theme_name):
        """主题被选中"""
        self.current_theme_idx = self.theme_names.index(theme_name)
        self.apply_theme()

    def cycle_theme(self):
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.theme_names)
        self.apply_theme()

    def apply_theme(self):
        theme_name = self.theme_names[self.current_theme_idx]
        t = THEMES[theme_name]
        self.theme_data = t
        self.btn_theme.setText(f"主题: {theme_name}")

        qss = f"""
        QMainWindow, QWidget {{
            background-color: {t['bg']};
            color: {t['fg']};
            font-family: 'Segoe UI', sans-serif;
        }}
        QFrame#Sidebar {{
            background-color: {t['sidebar']};
            border-right: 1px solid {t['border']};
        }}
        QLabel#AppTitle {{
            color: {t['fg']};
            font-size: 16pt;
            font-weight: bold;
        }}
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
        QLineEdit, QTextEdit {{
            background-color: {t['input_bg']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            color: {t['fg']};
            padding: 8px;
        }}
        QLineEdit:focus {{
            border: 1px solid {t['accent']};
        }}
        QGroupBox {{
            border: 1px solid {t['border']};
            border-radius: 8px;
            margin-top: 10px;
            color: {t['text_sec']};
        }}
        QListWidget {{
            background-color: {t['list_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px;
        }}
        QListWidget::item:selected {{
            background-color: {t['accent']}33;
            border-left: 3px solid {t['accent']};
        }}
        QProgressBar {{
            background-color: {t['input_bg']};
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background-color: {t['accent']};
        }}
        QCheckBox {{
            spacing: 8px;
            color: {t['fg']};
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid {t['border']};
            background: {t['input_bg']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {t['accent']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {t['accent']};
            border-color: {t['accent']};
            image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20'%3E%3Cpath d='M4 10 L8 14 L16 6' stroke='white' stroke-width='3' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
        }}
        """
        self.setStyleSheet(qss)
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
            added_count = 0
            for f in files:
                if f not in existing:
                    ui["list"].addItem(f)
                    added_count += 1
                    sys_logger.log(f"添加文件: {f}")
            self.append_log(f"添加了 {added_count} 个文件到队列")
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

        files = [ui["list"].item(i).text() for i in range(count)]
        path = self.custom_enc_path if is_encrypt else self.custom_dec_path

        # 新旧系统不同的验证
        if self.use_new_system:
            # 新系统
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
            # 老系统
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
        """新系统加密/解密（简化版，暂不支持所有高级功能）"""
        from core.rsa_cipher import RSAFileCipher

        task_type = "加密" if is_encrypt else "解密"
        sys_logger.log(f"========== [新系统] 开始{task_type}任务 ==========")
        sys_logger.log(f"文件数量: {len(files)}")
        sys_logger.log(f"密钥: {os.path.basename(key_path)}")

        ui["list"].setEnabled(False)
        ui["stack"].setCurrentIndex(1)
        ui["pbar"].setValue(0)
        ui["status"].setText("初始化引擎...")

        results = {"success": [], "fail": []}
        total = len(files)

        for idx, f in enumerate(files):
            try:
                fname = os.path.basename(f)
                out_dir = path if path else os.path.dirname(f)
                if is_encrypt:
                    out_path = os.path.join(out_dir, fname + ".enc")
                    success, msg = RSAFileCipher.encrypt_file(f, out_path, key_path)
                else:
                    out_path = os.path.join(out_dir, fname.replace(".enc", ""))
                    success, msg = RSAFileCipher.decrypt_file(f, out_path, key_path, key_pwd)

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

        # 详细日志记录
        task_type = "加密" if is_encrypt else "解密"
        sys_logger.log(f"========== 开始{task_type}任务 ==========")
        sys_logger.log(f"任务类型: {task_type}")
        sys_logger.log(f"文件数量: {count}")
        sys_logger.log(f"输出目录: {path if path else '原地覆盖'}")
        sys_logger.log(f"保留目录结构: {keep_struct}")
        sys_logger.log(f"{'加密' if is_encrypt else '解密'}文件夹名: {enc_dirname}")
        sys_logger.log(f"SSD 加速: {use_ssd}")
        if use_ssd:
            sys_logger.log(f"SSD 缓存路径: {ssd_path}")
        if is_encrypt:
            sys_logger.log(f"混淆文件名: {ui['chk_name'].isChecked()}")
            sys_logger.log(f"完成后粉碎源文件: {ui['chk_del'].isChecked()}")
        else:
            sys_logger.log(f"解密后移除加密包: {ui['chk_del'].isChecked()}")
        sys_logger.log("待处理文件列表:")
        for i, f in enumerate(files, 1):
            sys_logger.log(f"  [{i}] {f}")
        self.append_log(f"启动{task_type}任务，共 {count} 个文件")

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
            # 新系统：显示.pem密钥对
            keys_dir = DIRS["KEYS"]
            for f in os.listdir(keys_dir):
                if f.endswith('_private.pem'):
                    key_name = f.replace('_private.pem', '')
                    self.key_list.addItem(f"🔐 {key_name}")
            sys_logger.log(f"[新系统] 刷新密钥列表，共 {self.key_list.count()} 个密钥对")
        else:
            # 老系统：显示提示信息
            self.key_list.addItem("老系统无需管理密钥，加密时直接输入密码即可")
            sys_logger.log(f"[老系统] 无需密钥管理")

    def action_switch_system(self):
        self.use_new_system = not self.use_new_system
        if self.use_new_system:
            self.lbl_system_status.setText("新加密系统")
            self.lbl_system_desc.setText("非对称加密 (RSA-2048)")
            self.btn_switch_system.setText("← 切换到老系统")
            self.old_system_widget.hide()
            self.new_system_widget.show()
            self.btn_gen_new.show()
            self.btn_import_new.show()
            self.lbl_enc_system.setText("🔹 新系统")
            if hasattr(self, 'lbl_dec_system'):
                self.lbl_dec_system.setText("🔹 新系统")
            # 切换加密/解密界面
            self.ui_enc["old_sec_widget"].hide()
            self.ui_enc["new_sec_widget"].show()
            self.ui_dec["old_sec_widget"].hide()
            self.ui_dec["new_sec_widget"].show()
            self.refresh_key_combos()
        else:
            self.lbl_system_status.setText("老加密系统")
            self.lbl_system_desc.setText("对称加密 (AES-256)")
            self.btn_switch_system.setText("切换到新系统 →")
            self.old_system_widget.show()
            self.new_system_widget.hide()
            self.btn_gen_new.hide()
            self.btn_import_new.hide()
            self.lbl_enc_system.setText("🔹 老系统")
            if hasattr(self, 'lbl_dec_system'):
                self.lbl_dec_system.setText("🔹 老系统")
            # 切换加密/解密界面
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

        # 公钥
        lbl_pub = QLabel("公钥文件:")
        lbl_pub.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_pub)

        h_pub = QHBoxLayout()
        txt_pub = QLineEdit()
        txt_pub.setPlaceholderText("选择公钥文件 (*_public.pem)")
        txt_pub.setReadOnly(True)
        btn_pub = QPushButton("浏览...")
        btn_pub.setFixedWidth(80)
        btn_pub.clicked.connect(lambda: self._select_key_file(txt_pub, "公钥"))
        h_pub.addWidget(txt_pub)
        h_pub.addWidget(btn_pub)
        layout.addLayout(h_pub)

        # 私钥
        lbl_priv = QLabel("私钥文件:")
        lbl_priv.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_priv)

        h_priv = QHBoxLayout()
        txt_priv = QLineEdit()
        txt_priv.setPlaceholderText("选择私钥文件 (*_private.pem)")
        txt_priv.setReadOnly(True)
        btn_priv = QPushButton("浏览...")
        btn_priv.setFixedWidth(80)
        btn_priv.clicked.connect(lambda: self._select_key_file(txt_priv, "私钥"))
        h_priv.addWidget(txt_priv)
        h_priv.addWidget(btn_priv)
        layout.addLayout(h_priv)

        layout.addStretch()

        # 确定/取消按钮
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

        # 检查是否已存在
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

        key_name = selected.text().replace("🔐 ", "")
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
