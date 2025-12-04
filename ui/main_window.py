import os
import time
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QCheckBox, QAbstractItemView,
                               QSplitter, QFrame, QGridLayout, QComboBox)
from PySide6.QtCore import QThread, Signal, QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QFont, QColor
from config import DIRS, CHUNK_SIZES
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger


# ================= 批量工作线程 =================
class BatchWorkerThread(QThread):
    progress = Signal(str, int, int)
    finished = Signal(dict)

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
        total = len(self.files)

        for idx, f_path in enumerate(self.files):
            if not self.running: break
            fname = os.path.basename(f_path)

            self.progress.emit(f"正在处理 [{idx + 1}/{total}]: {fname}", 0, int((idx / total) * 100))

            def cb(curr, tot):
                p = int((curr / tot) * 100)
                if p % 2 == 0:
                    self.progress.emit(f"正在处理 [{idx + 1}/{total}]: {fname}", p, int((idx / total) * 100))

            # 路径逻辑
            if self.custom_out and os.path.exists(self.custom_out):
                out_dir = self.custom_out
            else:
                out_dir = os.path.dirname(f_path)

            suc, msg, out = engine.process_file(
                f_path, out_dir, key_bytes, self.is_enc, self.enc_name, cb
            )

            if suc:
                results["success"].append((f_path, out))
            else:
                results["fail"].append((f_path, msg))

        self.progress.emit("任务队列完成", 100, 100)
        self.finished.emit(results)

    def stop(self):
        self.running = False


# ================= 主界面 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Encryption Studio v6.8 (Auto-Log Refresh)")
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
        self._init_log_tab()  # 在这里启动了日志定时器

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

            QListWidget, QTextEdit, QLineEdit { background: #252526; border: 1px solid #3e3e42; color: #fff; border-radius: 4px; padding: 5px; }
            QListWidget::item:selected { background: #007acc; }

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
        left_grp = QGroupBox("1. 文件队列")
        l_left = QVBoxLayout(left_grp)
        l_left.setContentsMargins(15, 25, 15, 15)

        lbl_hint = QLabel("💡 提示：点击“添加文件”或拖入文件。")
        lbl_hint.setStyleSheet("color: #888; margin-bottom: 5px;")
        l_left.addWidget(lbl_hint)

        self.enc_list = QListWidget()
        self.enc_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

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
        left_grp = QGroupBox("1. 加密文件队列 (.enc)")
        l_left = QVBoxLayout(left_grp)
        l_left.setContentsMargins(15, 25, 15, 15)

        self.dec_list = QListWidget()
        self.dec_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

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

    # ================= [Tab 3] 日志 (含自动刷新) =================
    def _init_log_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(20, 30, 20, 20)

        # 头部说明
        head_l = QHBoxLayout()
        head_l.addWidget(QLabel("📝 系统运行日志 (每秒自动刷新)"))
        head_l.addStretch()

        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        self.log_txt.setStyleSheet("background: #111; color: #0f0; font-family: Consolas;")

        l.addLayout(head_l)
        l.addWidget(self.log_txt)
        self.tabs.addTab(tab, "🛡️ 系统日志")

        # [新功能] 启动 1秒 定时刷新
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.load_log)
        self.log_timer.start(1000)  # 1000ms = 1s

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
            files, _ = QFileDialog.getOpenFileNames(self, "添加文件", "", "All Files (*)")
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
        sys_logger.log(f"任务结束. {msg.replace(chr(10), ', ')}")

    def toggle_ui(self, enable):
        self.tabs.setEnabled(enable)

    def open_last_folder(self):
        if self.last_out_dir and os.path.exists(self.last_out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out_dir))
        else:
            QMessageBox.information(self, "提示", "尚未生成输出文件，无法打开目录。")

    # [优化版] 自动刷新日志
    def load_log(self):
        try:
            log_dir = DIRS["LOGS"]
            if not os.path.exists(log_dir): return

            files = sorted(os.listdir(log_dir))
            if not files: return

            target_log = os.path.join(log_dir, files[-1])
            with open(target_log, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            # [关键] 防抖：只有内容变了才刷新界面
            if content == self.log_txt.toPlainText():
                return

            # [关键] 保持滚动条位置
            scrollbar = self.log_txt.verticalScrollBar()
            was_at_bottom = scrollbar.value() == scrollbar.maximum()

            self.log_txt.setText(content)

            # 如果之前在底部，刷新后继续保持底部；否则保持当前阅读位置
            if was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())
            else:
                scrollbar.setValue(min(scrollbar.value(), scrollbar.maximum()))

        except Exception:
            pass