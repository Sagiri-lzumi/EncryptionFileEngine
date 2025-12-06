import os
import time
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QAbstractItemView,
                               QFrame, QStackedWidget, QApplication, QCheckBox)
from PySide6.QtCore import QThread, Signal, Qt, QUrl, QTimer, QMutex, QObject
from PySide6.QtGui import QDesktopServices, QPainter, QColor, QAction

# ================= 导入检测 =================
try:
    from config import DIRS
    from core.file_cipher import FileCipherEngine
    from core.logger import sys_logger
except ImportError:
    # 模拟环境
    DIRS = {"LOGS": "logs"}
    if not os.path.exists("logs"): os.makedirs("logs")


    class sys_logger:
        @staticmethod
        def log(msg, level="info"): print(f"[Log] {msg}")

# ================= 样式表 (已修改进度条颜色) =================

DARK_THEME = """
QMainWindow, QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Segoe UI', 'Microsoft YaHei'; font-size: 10pt; }
QGroupBox { border: 1px solid #3e3e42; border-radius: 4px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #007acc; background-color: #1e1e1e; }
QListWidget, QTextEdit, QLineEdit { background-color: #252526; border: 1px solid #3e3e42; border-radius: 2px; color: #d4d4d4; }
QLineEdit:focus, QTextEdit:focus { border: 1px solid #007acc; }
QPushButton { background-color: #3e3e42; color: #ffffff; border: 1px solid #3e3e42; padding: 6px 12px; border-radius: 2px; }
QPushButton:hover { background-color: #505050; border-color: #007acc; }
QPushButton:pressed { background-color: #007acc; }
QPushButton:disabled { background-color: #2d2d30; color: #666; border-color: #2d2d30; }
/* 强调按钮 */
QPushButton[class="primary"] { background-color: #007acc; border: 1px solid #007acc; }
QPushButton[class="primary"]:hover { background-color: #1c97ea; border-color: #1c97ea; }
QPushButton[class="danger"] { background-color: #c50500; border: 1px solid #c50500; }
QPushButton[class="danger"]:hover { background-color: #f00; border-color: #f00; }
/* 进度条 - 文字改为亮紫色 #E040FB，加粗防止看不清 */
QProgressBar { 
    border: 1px solid #3e3e42; 
    background-color: #2d2d30; 
    height: 16px; 
    border-radius: 2px; 
    text-align: center; 
    color: #E040FB; 
    font-weight: bold;
}
QProgressBar::chunk { background-color: #007acc; width: 10px; margin: 0.5px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #2d2d30; color: #888; padding: 8px 25px; border-top: 2px solid transparent; }
QTabBar::tab:selected { background: #1e1e1e; color: #007acc; border-top: 2px solid #007acc; }
"""

LIGHT_THEME = """
QMainWindow, QWidget { background-color: #f0f0f0; color: #333333; font-family: 'Segoe UI', 'Microsoft YaHei'; font-size: 10pt; }
QGroupBox { border: 1px solid #c0c0c0; border-radius: 4px; margin-top: 10px; padding-top: 15px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #005a9e; background-color: #f0f0f0; }
QListWidget, QTextEdit, QLineEdit { background-color: #ffffff; border: 1px solid #c0c0c0; border-radius: 2px; color: #333; }
QLineEdit:focus, QTextEdit:focus { border: 1px solid #005a9e; }
QPushButton { background-color: #ffffff; color: #333; border: 1px solid #c0c0c0; padding: 6px 12px; border-radius: 2px; }
QPushButton:hover { background-color: #eef6fb; border-color: #005a9e; }
QPushButton:pressed { background-color: #cce4f7; }
/* 强调按钮 */
QPushButton[class="primary"] { background-color: #005a9e; color: white; border: 1px solid #005a9e; }
QPushButton[class="primary"]:hover { background-color: #004578; border-color: #004578; }
QPushButton[class="danger"] { background-color: #d13438; color: white; border: 1px solid #d13438; }
QPushButton[class="danger"]:hover { background-color: #a4262c; border-color: #a4262c; }
/* 进度条 - 文字改为深紫色 #800080，加粗防止看不清 */
QProgressBar { 
    border: 1px solid #c0c0c0; 
    background-color: #e0e0e0; 
    height: 16px; 
    border-radius: 2px; 
    text-align: center; 
    color: #800080; 
    font-weight: bold;
}
QProgressBar::chunk { background-color: #005a9e; width: 10px; margin: 0.5px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #e0e0e0; color: #666; padding: 8px 25px; border-top: 2px solid transparent; }
QTabBar::tab:selected { background: #f0f0f0; color: #005a9e; border-top: 2px solid #005a9e; }
"""


# ================= 组件：拖拽列表 (已升级文件夹递归支持) =================
class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.theme_mode = "dark"

    def dragEnterEvent(self, e):
        # 只要有文件路径就允许拖入
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dragMoveEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            added = False

            # 1. 获取当前列表中已存在的文件，防止重复添加
            existing_files = set()
            for i in range(self.count()):
                existing_files.add(self.item(i).text())

            # 2. 遍历拖入的所有对象
            for url in e.mimeData().urls():
                path = url.toLocalFile()

                # 情况 A: 拖入的是单个文件
                if os.path.isfile(path):
                    if path not in existing_files:
                        self.addItem(path)
                        existing_files.add(path)  # 立即加入集合，防止同一次操作中有重复
                        added = True

                # 情况 B: 拖入的是文件夹 (新增功能)
                elif os.path.isdir(path):
                    # os.walk 自动递归遍历所有子文件夹
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            # 归一化路径分隔符，防止 Windows/Mac 混用导致判定失效
                            full_path = os.path.normpath(full_path)

                            if full_path not in existing_files:
                                self.addItem(full_path)
                                existing_files.add(full_path)
                                added = True

            # 3. 如果有新文件添加，尝试刷新 UI 状态
            if added and self.window():
                try:
                    # 这里的 logic 判断当前是否在加密页 (index 0)
                    self.window().reset_ui_state(self.window().tabs.currentIndex() == 0)
                except:
                    pass

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.save()
            # 根据主题调整文字颜色
            color = QColor("#666666") if self.theme_mode == "dark" else QColor("#999999")
            painter.setPen(color)
            font = self.font()
            font.setPointSize(10)
            painter.setFont(font)
            # 提示文字稍微改一下，体现支持文件夹
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, "请将文件或文件夹拖入此区域")
            painter.restore()


# ================= 辅助函数：文件大小格式化 =================
def format_size(size_bytes):
    """将字节转换为易读格式 (KB, MB, GB)"""
    if size_bytes == 0: return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


# ================= 核心：工作线程 (日志升级版) =================
class BatchWorkerThread(QThread):
    # 信号定义
    sig_progress = Signal(str, int)  # 文本, 百分比
    sig_log = Signal(str)  # 日志文本
    sig_finished = Signal(dict)  # 完成信号

    def __init__(self, files, key, is_encrypt, encrypt_filename=False, custom_out_dir=None):
        super().__init__()
        self.files = files
        self.key = key
        self.is_enc = is_encrypt
        self.enc_name = encrypt_filename
        self.custom_out = custom_out_dir

        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_flag = False

        self.total_bytes = 0
        self.file_progress_map = {}
        self.progress_lock = threading.Lock()
        self.last_emit_time = 0

    def is_stop_requested(self):
        return self._stop_flag

    def wait_if_paused(self):
        self._pause_event.wait()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_flag = True
        self._pause_event.set()

    def _engine_callback(self, file_path, current_processed, file_total):
        if self._stop_flag: return

        with self.progress_lock:
            self.file_progress_map[file_path] = current_processed
            total_processed = sum(self.file_progress_map.values())

            if self.total_bytes > 0:
                pct = int((total_processed / self.total_bytes) * 100)
            else:
                pct = 0

        # 节流控制：每 100ms 刷新一次
        current_time = time.time()
        if current_time - self.last_emit_time > 0.1 or pct == 100:
            # 进度条提示也稍微详细一点
            fname = os.path.basename(file_path)
            self.sig_progress.emit(f"正在处理: {fname} ({pct}%)", pct)
            self.last_emit_time = current_time

    def run(self):
        engine = FileCipherEngine()
        key_bytes = hashlib.sha256(self.key.encode()).digest()
        results = {"success": [], "fail": []}

        self.sig_log.emit("--- 系统正在计算任务队列 ---")
        self.total_bytes = 0
        self.file_progress_map = {}
        valid_files = []

        # 预扫描
        for f in self.files:
            if os.path.exists(f):
                size = os.path.getsize(f)
                self.total_bytes += size
                self.file_progress_map[f] = 0
                valid_files.append(f)
            else:
                results["fail"].append((f, "文件不存在"))
                self.sig_log.emit(f"⚠ [跳过] 文件不存在: {f}")

        if self.total_bytes == 0 and valid_files:
            self.total_bytes = 1

        action_str = "加密" if self.is_enc else "解密"
        total_size_str = format_size(self.total_bytes)
        self.sig_log.emit(
            f" [启动任务] 模式: {action_str} | 文件数: {len(valid_files)} | 总大小: {total_size_str}")

        max_workers = min(os.cpu_count() or 4, 4)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}

            for f_path in valid_files:
                if self._stop_flag: break

                out_dir = self.custom_out if (self.custom_out and os.path.exists(self.custom_out)) else os.path.dirname(
                    f_path)

                def specific_callback(p, t):
                    self._engine_callback(f_path, p, t)

                future = executor.submit(
                    engine.process_file,
                    f_path,
                    out_dir,
                    key_bytes,
                    self.is_enc,
                    self.enc_name,
                    specific_callback,
                    self
                )
                future_to_file[future] = f_path

            for future in as_completed(future_to_file):
                f_path = future_to_file[future]
                fname = os.path.basename(f_path)

                # 获取文件大小用于日志显示
                f_size_str = "未知大小"
                if os.path.exists(f_path):
                    f_size_str = format_size(os.path.getsize(f_path))

                try:
                    success, msg, out_path = future.result()
                    if success:
                        results["success"].append((f_path, out_path))
                        # 【详细日志】 成功
                        out_name = os.path.basename(out_path)
                        self.sig_log.emit(f" [成功] {fname} ({f_size_str}) -> {out_name}")
                    else:
                        if msg == "用户停止":
                            self.sig_log.emit(f" [中断] {fname}")
                        else:
                            results["fail"].append((f_path, msg))
                            # 【详细日志】 失败
                            self.sig_log.emit(f" [失败] {fname} ({f_size_str}) | 原因: {msg}")
                except Exception as e:
                    results["fail"].append((f_path, str(e)))
                    self.sig_log.emit(f" [异常] {fname} | 错误信息: {e}")

        final_msg = " 任务已强制终止" if self._stop_flag else " 所有任务处理完成"
        pct = 0 if self._stop_flag else 100
        self.sig_progress.emit(final_msg, pct)
        self.sig_finished.emit(results)
# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Security Engine Enterprise")
        self.resize(1080, 750)
        self.setMinimumSize(950, 650)

        # [修改] 默认为白天模式 (False)
        self.is_dark = False
        self.custom_enc_path = None
        self.custom_dec_path = None
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

        # 1. 顶部状态栏
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(50)
        hl = QHBoxLayout(self.top_bar)
        hl.setContentsMargins(20, 0, 20, 0)

        self.lbl_title = QLabel("安全加密引擎内核 | 系统就绪")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 11pt; color: #007acc;")
        hl.addWidget(self.lbl_title)
        hl.addStretch()

        self.btn_theme = QPushButton("切换显示模式")
        self.btn_theme.setFixedSize(110, 32)
        self.btn_theme.clicked.connect(self.toggle_theme)
        hl.addWidget(self.btn_theme)

        main_layout.addWidget(self.top_bar)

        # 2. 选项卡
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self._init_tab_encrypt()
        self._init_tab_decrypt()
        self._init_tab_log()

    def _create_common_layout(self, is_encrypt):
        page = QWidget()
        h_layout = QHBoxLayout(page)
        h_layout.setContentsMargins(25, 25, 25, 25)
        h_layout.setSpacing(25)

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

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_del)
        btn_bar.addWidget(btn_clr)

        v_left.addWidget(file_list)
        v_left.addLayout(btn_bar)

        grp_right = QGroupBox("执行参数配置")
        grp_right.setFixedWidth(400)
        v_right = QVBoxLayout(grp_right)
        v_right.setSpacing(18)

        v_right.addWidget(QLabel("安全密钥:"))
        txt_pwd = QLineEdit()
        txt_pwd.setEchoMode(QLineEdit.Password)
        txt_pwd.setPlaceholderText("请输入加密/解密专用密钥")
        txt_pwd.setMinimumHeight(38)
        v_right.addWidget(txt_pwd)

        v_right.addWidget(QLabel("输出路径:"))
        h_path = QHBoxLayout()
        txt_path = QLineEdit("默认: 源文件所在目录")
        txt_path.setReadOnly(True)
        btn_path = QPushButton("浏览...")
        btn_path.setFixedWidth(80)
        btn_path.clicked.connect(lambda: self.action_select_dir(is_encrypt))
        h_path.addWidget(txt_path)
        h_path.addWidget(btn_path)
        v_right.addLayout(h_path)

        chk_name = None
        chk_del = None
        if is_encrypt:
            chk_name = QCheckBox("启用文件名混淆 (推荐)")
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
        v_right.addSpacing(15)

        stack = QStackedWidget()

        w_start = QWidget()
        l_start = QVBoxLayout(w_start)
        l_start.setContentsMargins(0, 0, 0, 0)
        btn_run = QPushButton(f"执行{'加密' if is_encrypt else '解密'}程序")
        btn_run.setProperty("class", "primary")
        btn_run.setMinimumHeight(48)
        btn_run.setFont(self.font())
        btn_run.clicked.connect(self.run_encrypt if is_encrypt else self.run_decrypt)
        l_start.addWidget(btn_run)
        stack.addWidget(w_start)

        w_ctrl = QWidget()
        l_ctrl = QHBoxLayout(w_ctrl)
        l_ctrl.setContentsMargins(0, 0, 0, 0)
        l_ctrl.setSpacing(10)

        btn_pause = QPushButton("挂起任务")
        btn_pause.setMinimumHeight(48)
        btn_pause.clicked.connect(self.action_toggle_pause)

        btn_stop = QPushButton("终止操作")
        btn_stop.setProperty("class", "danger")
        btn_stop.setMinimumHeight(48)
        btn_stop.clicked.connect(self.action_stop_task)

        l_ctrl.addWidget(btn_pause)
        l_ctrl.addWidget(btn_stop)
        stack.addWidget(w_ctrl)

        w_res = QWidget()
        l_res = QHBoxLayout(w_res)
        l_res.setContentsMargins(0, 0, 0, 0)
        l_res.setSpacing(10)

        btn_open = QPushButton("打开输出目录")
        btn_open.setMinimumHeight(48)
        btn_open.clicked.connect(self.action_open_folder)

        btn_back = QPushButton("返回继续工作")
        btn_back.setMinimumHeight(48)
        btn_back.clicked.connect(lambda: self.reset_ui_state(is_encrypt))

        l_res.addWidget(btn_open)
        l_res.addWidget(btn_back)
        stack.addWidget(w_res)

        v_right.addWidget(stack)

        h_layout.addWidget(grp_left, 6)
        h_layout.addWidget(grp_right, 4)

        refs = {
            "list": file_list, "pwd": txt_pwd, "path": txt_path,
            "chk_name": chk_name, "chk_del": chk_del,
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
        vl = QVBoxLayout(page)
        vl.setContentsMargins(25, 25, 25, 25)

        grp = QGroupBox("系统运行日志")
        v = QVBoxLayout(grp)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        v.addWidget(self.txt_log)

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

        # [关键] 修复崩溃问题
        self.ui_enc["list"].viewport().update()
        self.ui_dec["list"].viewport().update()

    def action_add_file(self, is_encrypt):
        self.reset_ui_state(is_encrypt)
        ui = self.ui_enc if is_encrypt else self.ui_dec
        flter = "所有文件 (*)" if is_encrypt else "加密文件 (*.enc)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", flter)
        if files:
            existing = set([ui["list"].item(i).text() for i in range(ui["list"].count())])
            for f in files:
                if f not in existing: ui["list"].addItem(f)

    def action_remove_file(self, lst, is_encrypt):
        self.reset_ui_state(is_encrypt)
        for item in lst.selectedItems():
            lst.takeItem(lst.row(item))

    def action_select_dir(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            if is_encrypt:
                self.custom_enc_path = d
                self.ui_enc["path"].setText(d)
            else:
                self.custom_dec_path = d
                self.ui_dec["path"].setText(d)

    def reset_ui_state(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        ui["stack"].setCurrentIndex(0)
        ui["pbar"].setValue(0)
        ui["status"].setText("等待指令")
        ui["list"].setEnabled(True)
        ui["pwd"].setEnabled(True)

    def run_encrypt(self):
        self._start_process(True)

    def run_decrypt(self):
        self._start_process(False)

    def _start_process(self, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec

        count = ui["list"].count()
        if count == 0:
            return QMessageBox.warning(self, "操作提示", "任务队列为空，请先添加文件。")
        pwd = ui["pwd"].text()
        if not pwd:
            return QMessageBox.warning(self, "安全提示", "必须输入密钥才能继续操作。")

        files = [ui["list"].item(i).text() for i in range(count)]
        path = self.custom_enc_path if is_encrypt else self.custom_dec_path

        ui["list"].setEnabled(False)
        ui["pwd"].setEnabled(False)
        ui["stack"].setCurrentIndex(1)
        ui["pbar"].setValue(0)
        ui["status"].setText("正在初始化加密引擎...")

        self.is_paused = False
        self.worker = BatchWorkerThread(
            files,
            pwd,
            is_encrypt,
            encrypt_filename=ui["chk_name"].isChecked() if is_encrypt else False,
            custom_out_dir=path
        )

        self.worker.sig_progress.connect(self.update_progress)
        self.worker.sig_log.connect(self.append_log)
        self.worker.sig_finished.connect(lambda r: self.on_finished(r, is_encrypt))

        self.worker.start()

    def update_progress(self, text, val):
        is_enc = (self.tabs.currentIndex() == 0)
        ui = self.ui_enc if is_enc else self.ui_dec
        ui["status"].setText(text)
        ui["pbar"].setValue(val)

    def append_log(self, text):
        t = time.strftime("%H:%M:%S")
        color = "#a0a0a0" if self.is_dark else "#666"
        self.txt_log.append(f"<span style='color:{color}'>[{t}]</span> {text}")

        # [新增] 同步写入到日志文件
        sys_logger.log(text)

    def action_toggle_pause(self):
        if not self.worker: return
        is_enc = (self.tabs.currentIndex() == 0)
        ui = self.ui_enc if is_enc else self.ui_dec

        if self.is_paused:
            self.worker.resume()
            self.is_paused = False
            ui["btn_pause"].setText("挂起任务")
            ui["status"].setText("正在处理...")
        else:
            self.worker.pause()
            self.is_paused = True
            ui["btn_pause"].setText("继续任务")
            ui["status"].setText("任务已挂起")

    def action_stop_task(self):
        if self.worker:
            if self.is_paused: self.worker.resume()
            self.worker.stop()
            self.append_log("用户请求终止操作...")

    def on_finished(self, results, is_encrypt):
        ui = self.ui_enc if is_encrypt else self.ui_dec
        ui["stack"].setCurrentIndex(2)
        ui["list"].setEnabled(True)
        ui["pwd"].setEnabled(True)

        # [新增] 任务完成后自动清空文件队列
        ui["list"].clear()

        if results["success"]:
            self.last_out_dir = os.path.dirname(results["success"][0][1])

        chk_del = ui["chk_del"]
        if chk_del.isChecked():
            self.append_log("正在执行安全删除...")
            for src, _ in results["success"]:
                try:
                    os.remove(src)
                    self.append_log(f"已移除源文件: {os.path.basename(src)}")
                except Exception as e:
                    self.append_log(f"移除失败 {src}: {e}")

        succ_count = len(results["success"])
        fail_count = len(results["fail"])

        if fail_count == 0:
            QMessageBox.information(self, "操作完成", f"所有任务已成功执行。\n处理文件数: {succ_count}")
        else:
            QMessageBox.warning(self, "完成 (含异常)", f"成功: {succ_count}\n失败: {fail_count}\n请检查日志审计面板。")

    def action_open_folder(self):
        if self.last_out_dir and os.path.exists(self.last_out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out_dir))
        else:
            QMessageBox.information(self, "提示", "尚未生成输出目录或目录不可达。")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())