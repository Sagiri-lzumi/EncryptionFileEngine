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
from core.text_cipher import TextCipher
from core.logger import sys_logger


# ================= 批量工作线程 =================
class BatchWorkerThread(QThread):
    progress = Signal(str, int, int)  # LogMsg, FilePct, TotalPct
    finished = Signal(dict)

    def __init__(self, files, key, is_encrypt, encrypt_filename=False, force_project_dir=False):
        super().__init__()
        self.files = files
        self.k = key
        self.is_enc = is_encrypt
        self.enc_name = encrypt_filename
        self.force_proj = force_project_dir
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

            # [路径逻辑]
            if self.force_proj:
                out_dir = DIRS["ENCRYPTED"] if self.is_enc else DIRS["DECRYPTED"]
            else:
                # 默认: 源文件同级目录
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
        self.setWindowTitle("EncryptionFileEngine")
        self.resize(1150, 800)
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
        top_bar.setFixedHeight(40)
        top_l = QHBoxLayout(top_bar)
        top_l.addWidget(QLabel("  🛡️ 安全核心: 活跃"))
        top_l.addStretch()
        top_l.addWidget(QLabel("用户: Administrator  "))
        layout.addWidget(top_bar)

        # 2. 内容 Tab
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._init_encrypt_tab()
        self._init_decrypt_tab()
        self._init_text_tab()
        self._init_log_tab()

        self.last_out_dir = ""

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #ccc; }
            QWidget { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 13px; color: #e0e0e0; }

            QTabWidget::pane { border: none; background: #1e1e1e; }
            QTabBar::tab { background: #2d2d30; color: #888; padding: 10px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1e1e1e; color: #007acc; border-top: 2px solid #007acc; }

            /* [UI修正] GroupBox 样式优化 */
            QGroupBox { 
                border: 1px solid #444; 
                border-radius: 6px; 
                margin-top: 25px; /* 顶部预留空间给标题 */
                padding-top: 15px; 
                font-weight: bold; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left;
                left: 15px; 
                top: 0px; /* 标题位置修正 */
                padding: 0 5px; 
                background: #1e1e1e; /* 背景遮挡边框 */
                color: #007acc; 
            }

            QListWidget, QTextEdit, QLineEdit { background: #252526; border: 1px solid #3e3e42; color: #fff; border-radius: 4px; padding: 5px; }
            QListWidget::item:selected { background: #007acc; }

            QPushButton { background: #3e3e42; color: #fff; border: 1px solid #555; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background: #505055; border-color: #007acc; }
            QPushButton#ActionBtn { background: #007acc; border: none; font-weight: bold; font-size: 14px; }
            QPushButton#ActionBtn:hover { background: #0062a3; }

            QProgressBar { border: none; background: #2d2d30; height: 6px; border-radius: 3px; }
            QProgressBar::chunk { background: #007acc; border-radius: 3px; }
        """)

    # ================= [Tab 1] 加密 =================
    def _init_encrypt_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # [UI修正] 强制增加顶部边距，防止标题被切掉
        # setContentsMargins(left, top, right, bottom)
        layout.setContentsMargins(20, 40, 20, 20)

        # --- 左侧：文件队列 ---
        left_grp = QGroupBox("1. 文件队列 (单文件/批量)")
        l_left = QVBoxLayout(left_grp)
        # [UI修正] 内部增加间距，防止列表顶到标题
        l_left.setContentsMargins(15, 30, 15, 15)

        lbl_hint = QLabel("💡 提示：点击“添加文件”或直接拖入。\n加密结果默认保存在源文件同级目录下。")
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

        # --- 右侧：设置与执行 ---
        right_grp = QGroupBox("2. 加密配置")
        right_grp.setFixedWidth(380)
        l_right = QVBoxLayout(right_grp)
        l_right.setContentsMargins(15, 30, 15, 15)  # 内部间距

        l_right.addWidget(QLabel("设置密码:"))
        self.enc_pwd = QLineEdit()
        self.enc_pwd.setPlaceholderText("在此输入密码...")
        self.enc_pwd.setEchoMode(QLineEdit.Password)
        l_right.addWidget(self.enc_pwd)

        l_right.addSpacing(20)

        self.lbl_chunk = QLabel("⚡ 分块策略: 智能自动托管")
        self.lbl_chunk.setStyleSheet("color: #4ec9b0; font-style: italic;")
        l_right.addWidget(self.lbl_chunk)

        # 路径选择
        self.chk_save_proj = QCheckBox("📂 另存到程序专用目录 (EncryptedFile)")
        self.chk_save_proj.setToolTip(
            "默认关闭：结果保存在源文件同级目录。\n开启后：结果保存在程序的 EncryptedFile 文件夹内。")
        self.chk_save_proj.setChecked(False)
        l_right.addWidget(self.chk_save_proj)

        self.chk_name = QCheckBox("🔏 混淆文件名 (防破解)")
        self.chk_name.setToolTip("勾选后，文件名将变为随机乱码，但解密时会自动还原。")
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
        self.btn_enc_run.setFixedHeight(45)
        self.btn_enc_run.clicked.connect(self.run_encrypt)

        self.btn_open_enc = QPushButton("📂 打开输出位置")
        self.btn_open_enc.setVisible(False)
        self.btn_open_enc.clicked.connect(self.open_last_folder)

        l_right.addWidget(self.enc_status)
        l_right.addWidget(self.enc_pbar)
        l_right.addSpacing(10)
        l_right.addWidget(self.btn_enc_run)
        l_right.addWidget(self.btn_open_enc)

        layout.addWidget(left_grp)
        layout.addWidget(right_grp)
        self.tabs.addTab(tab, "🔒 加密工作台")

    # ================= [Tab 2] 解密 =================
    def _init_decrypt_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # [UI修正] 顶部边距
        layout.setContentsMargins(20, 40, 20, 20)

        # 左侧列表
        left_grp = QGroupBox("1. 加密文件队列 (.enc)")
        l_left = QVBoxLayout(left_grp)
        l_left.setContentsMargins(15, 30, 15, 15)

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

        # 右侧设置
        right_grp = QGroupBox("2. 解密配置")
        right_grp.setFixedWidth(380)
        l_right = QVBoxLayout(right_grp)
        l_right.setContentsMargins(15, 30, 15, 15)

        l_right.addWidget(QLabel("解密密码:"))
        self.dec_pwd = QLineEdit();
        self.dec_pwd.setEchoMode(QLineEdit.Password)
        l_right.addWidget(self.dec_pwd)

        l_right.addSpacing(20)

        # 路径选择
        self.chk_dec_proj = QCheckBox("📂 另存到程序专用目录 (DecryptedFile)")
        self.chk_dec_proj.setChecked(False)
        l_right.addWidget(self.chk_dec_proj)

        self.chk_dec_del = QCheckBox("⚠️ 解密后清理加密包 (.enc)")
        self.chk_dec_del.setChecked(False)
        l_right.addWidget(self.chk_dec_del)

        l_right.addStretch()

        self.dec_status = QLabel("等待任务...")
        self.dec_pbar = QProgressBar()

        self.btn_dec_run = QPushButton("🔓 开始解密")
        self.btn_dec_run.setObjectName("ActionBtn")
        self.btn_dec_run.setStyleSheet("background-color: #2e7d32;")
        self.btn_dec_run.setFixedHeight(45)
        self.btn_dec_run.clicked.connect(self.run_decrypt)

        self.btn_open_dec = QPushButton("📂 打开输出位置")
        self.btn_open_dec.setVisible(False)
        self.btn_open_dec.clicked.connect(self.open_last_folder)

        l_right.addWidget(self.dec_status)
        l_right.addWidget(self.dec_pbar)
        l_right.addSpacing(10)
        l_right.addWidget(self.btn_dec_run)
        l_right.addWidget(self.btn_open_dec)

        layout.addWidget(left_grp)
        layout.addWidget(right_grp)
        self.tabs.addTab(tab, "🔓 解密工作台")

    # ================= [Tab 3] 文本 =================
    def _init_text_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 40, 20, 20)

        top = QFrame()
        top.setStyleSheet("background: #252526; border-radius: 4px;")
        t_l = QHBoxLayout(top)
        self.txt_algo = QComboBox();
        self.txt_algo.addItems(["AES", "DES", "TripleDES", "RC4", "Base64", "MD5"])
        self.txt_key = QLineEdit();
        self.txt_key.setPlaceholderText("密钥 (Hash忽略)")
        t_l.addWidget(QLabel("算法:"));
        t_l.addWidget(self.txt_algo)
        t_l.addWidget(QLabel("密钥:"));
        t_l.addWidget(self.txt_key)
        layout.addWidget(top)

        splitter = QSplitter(Qt.Horizontal)

        w_left = QWidget()
        l_left = QVBoxLayout(w_left)
        l_left.addWidget(QLabel("📄 原文"))
        self.txt_in_enc = QTextEdit()
        self.txt_out_enc = QTextEdit();
        self.txt_out_enc.setReadOnly(True)
        btn_enc = QPushButton("⬇️ 加密");
        btn_enc.clicked.connect(self.do_txt_enc)
        l_left.addWidget(self.txt_in_enc);
        l_left.addWidget(btn_enc);
        l_left.addWidget(self.txt_out_enc)

        w_right = QWidget()
        r_l = QVBoxLayout(w_right)
        r_l.addWidget(QLabel("📄 密文"))
        self.txt_in_dec = QTextEdit()
        self.txt_out_dec = QTextEdit();
        self.txt_out_dec.setReadOnly(True)
        btn_dec = QPushButton("⬇️ 解密");
        btn_dec.clicked.connect(self.do_txt_dec)
        r_l.addWidget(self.txt_in_dec);
        r_l.addWidget(btn_dec);
        r_l.addWidget(self.txt_out_dec)

        splitter.addWidget(w_left)
        splitter.addWidget(w_right)
        layout.addWidget(splitter)

        self.tabs.addTab(tab, "📝 文本工具")

    # ================= [Tab 4] 日志 =================
    def _init_log_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(20, 40, 20, 20)  # 统一间距
        self.log_txt = QTextEdit();
        self.log_txt.setReadOnly(True)
        btn = QPushButton("刷新日志");
        btn.clicked.connect(self.load_log)
        l.addWidget(btn);
        l.addWidget(self.log_txt)
        self.tabs.addTab(tab, "🛡️ 系统日志")

    # ================= 逻辑方法 =================
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

        # 传递是否强制存入项目目录的参数
        self.worker = BatchWorkerThread(
            files, key, True,
            encrypt_filename=self.chk_name.isChecked(),
            force_project_dir=self.chk_save_proj.isChecked()
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
            force_project_dir=self.chk_dec_proj.isChecked()
        )
        self.worker.progress.connect(lambda msg, s, t: (self.dec_status.setText(msg), self.dec_pbar.setValue(t)))
        self.worker.finished.connect(lambda res: self.on_finish(res, False))
        self.worker.start()

    def on_finish(self, results, is_enc):
        self.toggle_ui(True)
        succ = len(results["success"])
        fail = len(results["fail"])
        del_count = 0

        # 记录最后一个成功的文件夹以便打开
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

    def do_txt_enc(self):
        try:
            res = TextCipher.encrypt(self.txt_in_enc.toPlainText(), self.txt_algo.currentText(), self.txt_key.text())
            self.txt_out_enc.setText(res)
        except Exception as e:
            self.txt_out_enc.setText(str(e))

    def do_txt_dec(self):
        algo = self.txt_algo.currentText()
        if algo == "Base64":
            import base64
            try:
                self.txt_out_dec.setText(base64.b64decode(self.txt_in_dec.toPlainText()).decode())
            except:
                self.txt_out_dec.setText("解码失败")
        else:
            self.txt_out_dec.setText("请在 core/text_cipher.py 实现对称解密逻辑")

    def load_log(self):
        try:
            f = sorted(os.listdir(DIRS["LOGS"]))[-1]
            with open(os.path.join(DIRS["LOGS"], f), 'r', encoding='utf-8-sig') as file:
                self.log_txt.setText(file.read())
        except:
            pass