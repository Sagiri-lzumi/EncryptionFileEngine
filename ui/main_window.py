import os
import time
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QCheckBox, QAbstractItemView,
                               QSplitter, QFrame, QGridLayout, QComboBox)
from PySide6.QtCore import QThread, Signal, QTimer, QUrl, Qt
# [回归] 引入拖拽事件
from PySide6.QtGui import QDesktopServices, QFont, QColor, QDragEnterEvent, QDropEvent
from config import DIRS, CHUNK_SIZES
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger


# =========================================================
# [回归功能] 支持拖拽文件的自定义列表控件
# =========================================================
class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # 开启拖拽接收
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # 样式优化
        self.setStyleSheet("""
            QListWidget {
                background: #252526; border: 1px solid #3e3e42; color: #fff; 
                border-radius: 4px; padding: 5px;
            }
            QListWidget::item:selected { background: #007acc; }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):  # 只接受文件
                    links.append(file_path)
            self.addItems(links)
        else:
            event.ignore()


# =========================================================
# 批量工作线程 (进度算法修正 + 日志增强)
# =========================================================
class BatchWorkerThread(QThread):
    # 信号: [状态栏文本, 当前文件进度, 全局进度]
    progress = Signal(str, int, int)
    finished = Signal(dict)
    # [回归] 实时日志信号
    log_update = Signal(str)

    def __init__(self, files, key, is_encrypt, encrypt_filename=False, custom_out_dir=None):
        super().__init__()
        self.files = files
        self.k = key
        self.is_enc = is_encrypt
        self.enc_name = encrypt_filename
        self.custom_out = custom_out_dir
        self.running = True

    def run(self):
        engine = FileCipherEngine()
        import hashlib
        key_bytes = hashlib.sha256(self.k.encode()).digest()

        results = {"success": [], "fail": []}
        total_files = len(self.files)
        action_str = "加密" if self.is_enc else "解密"

        # [日志] 开始记录
        start_msg = f"--- 开始批量{action_str}任务 (共 {total_files} 个文件) ---"
        self.log_update.emit(start_msg)
        sys_logger.log(start_msg)

        for idx, f_path in enumerate(self.files):
            if not self.running: break
            fname = os.path.basename(f_path)
            start_t = time.time()

            # 全局进度基数
            global_base_pct = (idx / total_files) * 100
            self.progress.emit(f"正在处理 [{idx + 1}/{total_files}]: {fname}", 0, int(global_base_pct))

            # 回调函数 (包含智能防抖)
            last_p = -1

            def cb(curr, tot):
                nonlocal last_p
                if tot == 0:
                    p = 0
                else:
                    p = int((curr / tot) * 100)

                if p > last_p:
                    last_p = p
                    current_global = int(((idx + (p / 100.0)) / total_files) * 100)
                    self.progress.emit(f"正在处理 [{idx + 1}/{total_files}]: {fname} ({p}%)", p, current_global)

            # 路径逻辑
            if self.custom_out and os.path.exists(self.custom_out):
                out_dir = self.custom_out
            else:
                out_dir = os.path.dirname(f_path)

            # 执行核心逻辑
            suc, msg, out_path = engine.process_file(
                f_path, out_dir, key_bytes, self.is_enc, self.enc_name, cb
            )

            duration = (time.time() - start_t) * 1000  # ms

            if suc:
                results["success"].append((f_path, out_path))
                # [回归] 详细日志记录
                out_name = os.path.basename(out_path)
                log_detail = f"[{action_str}成功] {fname} -> {out_name} (耗时: {int(duration)}ms)"
                self.log_update.emit(log_detail)
                sys_logger.log(log_detail)
            else:
                results["fail"].append((f_path, msg))
                log_fail = f"[{action_str}失败] {fname} | 原因: {msg}"
                self.log_update.emit(log_fail)
                sys_logger.log(log_fail, "error")

        self.progress.emit("任务队列完成", 100, 100)
        self.finished.emit(results)

    def stop(self):
        self.running = False


# ================= 主界面 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Encryption Studio v7.2 (Full Features)")
        self.resize(1100, 780)
        self.setMinimumSize(950, 650)
        self._apply_theme()

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 顶部状态条
        top_bar = QFrame()
        top_bar.setStyleSheet("background: #252526; border-bottom: 1px solid #333;")
        top_bar.setMinimumHeight(50)
        top_l = QHBoxLayout(top_bar)
        top_l.addWidget(QLabel("  🛡️ 安全核心: 活跃"))
        top_l.addStretch()
        layout.addWidget(top_bar)

        # 2. 内容 Tab
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 状态变量
        self.custom_enc_path = None
        self.custom_dec_path = None
        self.last_out_dir = ""

        self._init_encrypt_tab()
        self._init_decrypt_tab()
        self._init_log_tab()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #ccc; }
            QWidget { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 13px; color: #e0e0e0; }

            QTabWidget::pane { border: none; background: #1e1e1e; }
            QTabBar::tab { background: #2d2d30; color: #888; padding: 12px 25px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1e1e1e; color: #007acc; border-top: 3px solid #007acc; }

            QGroupBox { 
                border: 1px solid #444; 
                border-radius: 6px; 
                margin-top: 25px; 
                font-weight: bold; 
                font-size: 14px;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left;
                left: 15px; 
                top: 0px; 
                padding: 0 5px; 
                background-color: #1e1e1e; 
                color: #007acc; 
            }

            QLineEdit { background: #252526; border: 1px solid #3e3e42; color: #fff; border-radius: 4px; padding: 5px; }

            QPushButton { background: #3e3e42; color: #fff; border: 1px solid #555; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background: #505055; border-color: #007acc; }
            QPushButton#ActionBtn { background: #007acc; border: none; font-weight: bold; font-size: 14px; padding: 12px; }
            QPushButton#ActionBtn:hover { background: #0062a3; }
            QPushButton#SmallBtn { padding: 4px 10px; font-size: 12px; }

            QProgressBar { border: none; background: #2d2d30; height: 8px; border-radius: 4px; }
            QProgressBar::chunk { background: #007acc; border-radius: 4px; }
        """)

    # ================= [Tab 1] 加密 =================
    def _init_encrypt_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 30, 20, 20)

        # --- 左侧 ---
        left_grp = QGroupBox("1. 文件队列 (支持拖拽)")
        l_left = QVBoxLayout(left_grp)
        l_left.setContentsMargins(15, 25, 15, 15)

        lbl_hint = QLabel("💡 提示：点击“添加文件”或将文件拖入下方区域。")
        lbl_hint.setStyleSheet("color: #888; margin-bottom: 5px;")
        l_left.addWidget(lbl_hint)

        # [回归] 使用 DragDropListWidget
        self.enc_list = DragDropListWidget()

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ 添加文件");
        btn_add.clicked.connect(lambda: self.add_files(True))
        btn_rem = QPushButton("➖ 移除选中");
        btn_rem.clicked.connect(lambda: self.remove_sel(self.enc_list))
        btn_clr = QPushButton("🗑️ 清空队列");
        btn_clr.clicked.connect(self.enc_list.clear)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_rem)
        btn_layout.addWidget(btn_clr)

        l_left.addWidget(self.enc_list)
        l_left.addLayout(btn_layout)

        # --- 右侧 ---
        right_grp = QGroupBox("2. 加密配置")
        right_grp.setFixedWidth(380)
        l_right = QVBoxLayout(right_grp)
        l_right.setContentsMargins(20, 25, 20, 20)

        l_right.addWidget(QLabel("设置密码:"))
        self.enc_pwd = QLineEdit()
        self.enc_pwd.setPlaceholderText("在此输入密码...")
        self.enc_pwd.setEchoMode(QLineEdit.Password)
        self.enc_pwd.setMinimumHeight(35)
        l_right.addWidget(self.enc_pwd)

        l_right.addSpacing(20)

        # 输出路径
        l_right.addWidget(QLabel("输出位置:"))
        path_layout = QHBoxLayout()
        self.lbl_enc_path = QLineEdit("默认: 源文件同级目录")
        self.lbl_enc_path.setReadOnly(True)
        self.lbl_enc_path.setStyleSheet("color: #aaa; font-style: italic;")

        btn_sel_path = QPushButton("📂 选择")
        btn_sel_path.setObjectName("SmallBtn")
        btn_sel_path.clicked.connect(lambda: self.select_out_dir(True))

        btn_rst_path = QPushButton("↺ 重置")
        btn_rst_path.setObjectName("SmallBtn")
        btn_rst_path.setToolTip("恢复为默认源文件目录")
        btn_rst_path.clicked.connect(lambda: self.reset_out_dir(True))

        path_layout.addWidget(self.lbl_enc_path)
        path_layout.addWidget(btn_sel_path)
        path_layout.addWidget(btn_rst_path)
        l_right.addLayout(path_layout)

        l_right.addSpacing(15)

        self.chk_name = QCheckBox("🔏 混淆文件名 (防破解)")
        self.chk_name.setChecked(True)
        l_right.addWidget(self.chk_name)

        self.chk_del = QCheckBox("⚠️ 完成后物理删除源文件")
        self.chk_del.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        self.chk_del.setChecked(False)
        l_right.addWidget(self.chk_del)

        l_right.addStretch()

        self.enc_status = QLabel("等待任务...")
        self.enc_pbar = QProgressBar()

        self.btn_enc_run = QPushButton("🚀 开始加密")
        self.btn_enc_run.setObjectName("ActionBtn")
        self.btn_enc_run.setMinimumHeight(50)
        self.btn_enc_run.clicked.connect(self.run_encrypt)

        self.btn_open_enc = QPushButton("📂 打开输出文件夹")
        self.btn_open_enc.setVisible(False)
        self.btn_open_enc.setMinimumHeight(40)
        self.btn_open_enc.clicked.connect(self.open_last_folder)

        l_right.addWidget(self.enc_status)
        l_right.addWidget(self.enc_pbar)
        l_right.addSpacing(15)
        l_right.addWidget(self.btn_enc_run)
        l_right.addWidget(self.btn_open_enc)

        layout.addWidget(left_grp)
        layout.addWidget(right_grp)
        self.tabs.addTab(tab, "🔒 加密工作台")

    # ================= [Tab 2] 解密 =================
    def _init_decrypt_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 30, 20, 20)

        # 左侧
        left_grp = QGroupBox("1. 加密文件队列 (支持拖拽)")
        l_left = QVBoxLayout(left_grp)
        l_left.setContentsMargins(15, 25, 15, 15)

        # [回归] 使用 DragDropListWidget
        self.dec_list = DragDropListWidget()

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ 添加文件");
        btn_add.clicked.connect(lambda: self.add_files(False))
        btn_rem = QPushButton("➖ 移除选中");
        btn_rem.clicked.connect(lambda: self.remove_sel(self.dec_list))
        btn_clr = QPushButton("🗑️ 清空队列");
        btn_clr.clicked.connect(self.dec_list.clear)
        btn_layout.addWidget(btn_add);
        btn_layout.addWidget(btn_rem);
        btn_layout.addWidget(btn_clr)
        l_left.addWidget(self.dec_list);
        l_left.addLayout(btn_layout)

        # 右侧
        right_grp = QGroupBox("2. 解密配置")
        right_grp.setFixedWidth(380)
        l_right = QVBoxLayout(right_grp)
        l_right.setContentsMargins(20, 25, 20, 20)

        l_right.addWidget(QLabel("解密密码:"))
        self.dec_pwd = QLineEdit();
        self.dec_pwd.setEchoMode(QLineEdit.Password)
        self.dec_pwd.setMinimumHeight(35)
        l_right.addWidget(self.dec_pwd)

        l_right.addSpacing(20)

        # 路径选择
        l_right.addWidget(QLabel("输出位置:"))
        path_layout = QHBoxLayout()
        self.lbl_dec_path = QLineEdit("默认: 源文件同级目录")
        self.lbl_dec_path.setReadOnly(True)
        self.lbl_dec_path.setStyleSheet("color: #aaa; font-style: italic;")

        btn_sel_path = QPushButton("📂 选择")
        btn_sel_path.setObjectName("SmallBtn")
        btn_sel_path.clicked.connect(lambda: self.select_out_dir(False))

        btn_rst_path = QPushButton("↺ 重置")
        btn_rst_path.setObjectName("SmallBtn")
        btn_rst_path.clicked.connect(lambda: self.reset_out_dir(False))

        path_layout.addWidget(self.lbl_dec_path)
        path_layout.addWidget(btn_sel_path)
        path_layout.addWidget(btn_rst_path)
        l_right.addLayout(path_layout)

        l_right.addSpacing(15)

        self.chk_dec_del = QCheckBox("⚠️ 解密后清理加密包 (.enc)")
        self.chk_dec_del.setChecked(False)
        self.chk_dec_del.setMinimumHeight(25)
        l_right.addWidget(self.chk_dec_del)

        l_right.addStretch()

        self.dec_status = QLabel("等待任务...")
        self.dec_pbar = QProgressBar()

        self.btn_dec_run = QPushButton("🔓 开始解密")
        self.btn_dec_run.setObjectName("ActionBtn")
        self.btn_dec_run.setStyleSheet("background-color: #2e7d32; border: none;")
        self.btn_dec_run.setMinimumHeight(50)
        self.btn_dec_run.clicked.connect(self.run_decrypt)

        self.btn_open_dec = QPushButton("📂 打开输出文件夹")
        self.btn_open_dec.setVisible(False)
        self.btn_open_dec.setMinimumHeight(40)
        self.btn_open_dec.clicked.connect(self.open_last_folder)

        l_right.addWidget(self.dec_status)
        l_right.addWidget(self.dec_pbar)
        l_right.addSpacing(15)
        l_right.addWidget(self.btn_dec_run)
        l_right.addWidget(self.btn_open_dec)

        layout.addWidget(left_grp)
        layout.addWidget(right_grp)
        self.tabs.addTab(tab, "🔓 解密工作台")

    # ================= [Tab 3] 日志 =================
    def _init_log_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(20, 30, 20, 20)

        head = QHBoxLayout()
        head.addWidget(QLabel("📝 实时操作日志 (自动刷新)"))
        head.addStretch()

        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        # 深色日志风格
        self.log_txt.setStyleSheet(
            "background: #1e1e1e; border: 1px solid #444; color: #9cdcfe; font-family: Consolas;")

        l.addLayout(head)
        l.addWidget(self.log_txt)
        self.tabs.addTab(tab, "🛡️ 系统日志")

        # 兜底定时刷新
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.load_log)
        self.log_timer.start(2000)  # 每2秒检查一次文件变化

    # ================= 逻辑方法 =================

    def select_out_dir(self, is_encrypt):
        d = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if d:
            if is_encrypt:
                self.custom_enc_path = d
                self.lbl_enc_path.setText(f"自定义: {d}")
                self.lbl_enc_path.setStyleSheet("color: #00e5ff; font-weight: bold;")
            else:
                self.custom_dec_path = d
                self.lbl_dec_path.setText(f"自定义: {d}")
                self.lbl_dec_path.setStyleSheet("color: #00e5ff; font-weight: bold;")

    def reset_out_dir(self, is_encrypt):
        if is_encrypt:
            self.custom_enc_path = None
            self.lbl_enc_path.setText("默认: 源文件同级目录")
            self.lbl_enc_path.setStyleSheet("color: #aaa; font-style: italic;")
        else:
            self.custom_dec_path = None
            self.lbl_dec_path.setText("默认: 源文件同级目录")
            self.lbl_dec_path.setStyleSheet("color: #aaa; font-style: italic;")

    def add_files(self, is_enc):
        if is_enc:
            files, _ = QFileDialog.getOpenFileNames(self, "添加文件 (可多选)", "", "All Files (*)")
            if files: self.enc_list.addItems(files)
        else:
            files, _ = QFileDialog.getOpenFileNames(self, "添加加密文件", "", "Encrypted (*.enc)")
            if files: self.dec_list.addItems(files)

    def remove_sel(self, list_w):
        for item in list_w.selectedItems():
            list_w.takeItem(list_w.row(item))

    def run_encrypt(self):
        files = [self.enc_list.item(i).text() for i in range(self.enc_list.count())]
        key = self.enc_pwd.text()

        if not files: return QMessageBox.warning(self, "提示", "请先添加文件")
        if not key: return QMessageBox.warning(self, "提示", "请输入密码")

        self.toggle_ui(False)
        self.enc_pbar.setValue(0)
        self.btn_open_enc.setVisible(False)

        self.worker = BatchWorkerThread(
            files, key, True,
            encrypt_filename=self.chk_name.isChecked(),
            custom_out_dir=self.custom_enc_path
        )
        self.worker.progress.connect(lambda msg, s, t: (self.enc_status.setText(msg), self.enc_pbar.setValue(t)))
        # [回归] 实时日志连接
        self.worker.log_update.connect(self.append_log_immediate)
        self.worker.finished.connect(lambda res: self.on_finish(res, True))
        self.worker.start()

    def run_decrypt(self):
        files = [self.dec_list.item(i).text() for i in range(self.dec_list.count())]
        key = self.dec_pwd.text()

        if not files or not key: return QMessageBox.warning(self, "提示", "请添加文件并输入密码")

        self.toggle_ui(False)
        self.dec_pbar.setValue(0)
        self.btn_open_dec.setVisible(False)

        self.worker = BatchWorkerThread(
            files, key, False, False,
            custom_out_dir=self.custom_dec_path
        )
        self.worker.progress.connect(lambda msg, s, t: (self.dec_status.setText(msg), self.dec_pbar.setValue(t)))
        # [回归] 实时日志连接
        self.worker.log_update.connect(self.append_log_immediate)
        self.worker.finished.connect(lambda res: self.on_finish(res, False))
        self.worker.start()

    def on_finish(self, results, is_enc):
        self.toggle_ui(True)
        succ = len(results["success"])
        fail = len(results["fail"])
        del_count = 0

        if succ > 0:
            last_file = results["success"][-1][1]
            self.last_out_dir = os.path.dirname(last_file)

        if is_enc and self.chk_del.isChecked():
            for src, _ in results["success"]:
                try:
                    os.remove(src); del_count += 1
                except:
                    pass
        elif not is_enc and self.chk_dec_del.isChecked():
            for src, _ in results["success"]:
                try:
                    os.remove(src); del_count += 1
                except:
                    pass

        msg = f"成功: {succ} 个\n失败: {fail} 个"
        if del_count > 0: msg += f"\n已物理删除源文件: {del_count} 个"

        if is_enc:
            self.enc_list.clear()
            self.btn_open_enc.setVisible(True)
            self.enc_status.setText("任务完成")
        else:
            self.dec_list.clear()
            self.btn_open_dec.setVisible(True)
            self.dec_status.setText("任务完成")

        QMessageBox.information(self, "结果报告", msg)

    def toggle_ui(self, enable):
        self.tabs.setEnabled(enable)

    def open_last_folder(self):
        if self.last_out_dir and os.path.exists(self.last_out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out_dir))
        else:
            QMessageBox.information(self, "提示", "尚未生成输出文件，无法打开目录。")

    # [回归] 实时追加日志
    def append_log_immediate(self, msg):
        self.log_txt.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.log_txt.verticalScrollBar().setValue(self.log_txt.verticalScrollBar().maximum())

    # 定时器读取文件 (用于捕获非实时日志或手动修改)
    def load_log(self):
        try:
            f = sorted(os.listdir(DIRS["LOGS"]))[-1]
            with open(os.path.join(DIRS["LOGS"], f), 'r', encoding='utf-8-sig') as file:
                content = file.read()

            if content == self.log_txt.toPlainText(): return

            sb = self.log_txt.verticalScrollBar()
            was_at_bottom = sb.value() == sb.maximum()

            self.log_txt.setText(content)

            if was_at_bottom:
                sb.setValue(sb.maximum())
            else:
                sb.setValue(min(sb.value(), sb.maximum()))
        except:
            pass