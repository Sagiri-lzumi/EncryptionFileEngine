import os
import time
import threading
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QCheckBox, QAbstractItemView,
                               QSplitter, QFrame, QGridLayout, QComboBox, QStackedWidget)
from PySide6.QtCore import QThread, Signal, QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QFont, QColor, QDragEnterEvent, QDropEvent
from config import DIRS, CHUNK_SIZES
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger


# ================= 拖拽列表 =================
class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setStyleSheet("background: #252526; border: 1px solid #444; color: #fff; border-radius: 4px;")

    def dragEnterEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dragMoveEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else None

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            for url in e.mimeData().urls():
                f = url.toLocalFile()
                if os.path.isfile(f): self.addItem(f)


# ================= 核心工作线程 (支持暂停/停止) =================
class BatchWorkerThread(QThread):
    progress = Signal(str, int, int)  # Msg, FilePct, TotalPct
    finished = Signal(dict)
    log_update = Signal(str)

    def __init__(self, files, key, is_encrypt, encrypt_filename=False, custom_out_dir=None):
        super().__init__()
        self.files = files
        self.k = key
        self.is_enc = is_encrypt
        self.enc_name = encrypt_filename
        self.custom_out = custom_out_dir

        # 控制信号
        self._pause_event = threading.Event()
        self._pause_event.set()  # True = 运行, False = 暂停
        self._stop_flag = False

    # 引擎回调接口
    def is_stop_requested(self):
        return self._stop_flag

    def wait_if_paused(self):
        self._pause_event.wait()

    # 外部控制接口
    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_flag = True
        self._pause_event.set()  # 必须唤醒才能停止

    def run(self):
        engine = FileCipherEngine()
        import hashlib
        key_bytes = hashlib.sha256(self.k.encode()).digest()

        results = {"success": [], "fail": []}
        total = len(self.files)
        action_str = "加密" if self.is_enc else "解密"

        self.log_update.emit(f"--- 任务开始: {action_str} {total} 个文件 ---")

        for idx, f_path in enumerate(self.files):
            if self._stop_flag: break

            fname = os.path.basename(f_path)
            start_t = time.time()

            # 全局基准进度
            global_base = (idx / total) * 100
            self.progress.emit(f"正在处理 [{idx + 1}/{total}]: {fname}", 0, int(global_base))

            # 实时进度回调
            last_p = -1

            def cb(curr, tot):
                nonlocal last_p
                if tot == 0:
                    p = 0
                else:
                    p = int((curr / tot) * 100)

                # 降低刷新频率防卡顿
                if p > last_p:
                    last_p = p
                    # 计算平滑的全局进度
                    cur_global = int(((idx + (p / 100.0)) / total) * 100)
                    self.progress.emit(f"处理中 [{idx + 1}/{total}]: {fname} ({p}%)", p, cur_global)

            # 路径
            if self.custom_out and os.path.exists(self.custom_out):
                out_dir = self.custom_out
            else:
                out_dir = os.path.dirname(f_path)

            # 执行 (传入 self 作为 controller)
            suc, msg, out_path = engine.process_file(
                f_path, out_dir, key_bytes, self.is_enc, self.enc_name, cb, controller=self
            )

            duration = (time.time() - start_t) * 1000

            if suc:
                results["success"].append((f_path, out_path))
                log_msg = f"[{action_str}成功] {fname} -> {os.path.basename(out_path)} ({int(duration)}ms)"
                self.log_update.emit(log_msg)
                sys_logger.log(log_msg)
            else:
                if msg == "用户停止":
                    self.log_update.emit(f"⚠️ {fname} 处理被中止")
                else:
                    results["fail"].append((f_path, msg))
                    self.log_update.emit(f"❌ {fname}: {msg}")
                    sys_logger.log(f"失败 {fname}: {msg}", "error")

        if self._stop_flag:
            self.progress.emit("任务已停止", 0, 0)
        else:
            self.progress.emit("任务完成", 100, 100)

        self.finished.emit(results)


# ================= 主界面 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Encryption Studio")
        self.resize(1100, 780)
        self.setMinimumSize(980, 680)
        self._apply_theme()

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部
        top_bar = QFrame()
        top_bar.setStyleSheet("background: #252526; border-bottom: 1px solid #333;")
        top_bar.setFixedHeight(50)
        tl = QHBoxLayout(top_bar)
        tl.addWidget(QLabel("  🛡️ 安全核心: 正常工作"))
        tl.addStretch()
        layout.addWidget(top_bar)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 变量
        self.custom_enc_path = None
        self.custom_dec_path = None
        self.last_out_dir = ""
        self.is_paused = False

        self._init_encrypt_tab()
        self._init_decrypt_tab()
        self._init_log_tab()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #ccc; }
            QWidget { font-family: 'Microsoft YaHei UI'; font-size: 10pt; color: #e0e0e0; }

            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #2d2d30; color: #999; padding: 10px 25px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1e1e1e; color: #007acc; border-top: 3px solid #007acc; font-weight: bold; }

            QGroupBox { border: 1px solid #444; border-radius: 6px; margin-top: 25px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; top: 0px; padding: 0 5px; background-color: #1e1e1e; color: #007acc; }

            QListWidget, QLineEdit { background: #252526; border: 1px solid #3e3e42; border-radius: 4px; padding: 6px; }
            QListWidget::item:selected { background: #007acc; }

            QPushButton { background: #3e3e42; color: #fff; border: 1px solid #555; padding: 6px 15px; border-radius: 4px; }
            QPushButton:hover { background: #505055; border-color: #007acc; }

            QPushButton#StartBtn { background: #007acc; border: none; font-weight: bold; font-size: 12pt; }
            QPushButton#StartBtn:hover { background: #0062a3; }

            QPushButton#PauseBtn { background: #f09000; border: none; font-weight: bold; }
            QPushButton#PauseBtn:hover { background: #c67600; }

            QPushButton#StopBtn { background: #d32f2f; border: none; font-weight: bold; }
            QPushButton#StopBtn:hover { background: #b71c1c; }

            QProgressBar { border: none; background: #2d2d30; height: 10px; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background: #007acc; border-radius: 5px; }
        """)

    # ================= 加密页 =================
    def _init_encrypt_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 30, 20, 20)

        # 左侧
        left_grp = QGroupBox("1. 文件队列")
        l_left = QVBoxLayout(left_grp)
        l_left.setContentsMargins(15, 25, 15, 15)
        l_left.addWidget(QLabel("💡 支持拖拽 / 多选"))

        self.enc_list = DragDropListWidget()
        btn_l = QHBoxLayout()
        b_add = QPushButton("➕ 添加");
        b_add.clicked.connect(lambda: self.add_files(True))
        b_del = QPushButton("➖ 移除");
        b_del.clicked.connect(lambda: self.remove_sel(self.enc_list))
        b_clr = QPushButton("🗑️ 清空");
        b_clr.clicked.connect(self.enc_list.clear)
        btn_l.addWidget(b_add);
        btn_l.addWidget(b_del);
        btn_l.addWidget(b_clr)
        l_left.addWidget(self.enc_list);
        l_left.addLayout(btn_l)

        # 右侧
        right_grp = QGroupBox("2. 配置与控制")
        right_grp.setFixedWidth(400)
        l_right = QVBoxLayout(right_grp)
        l_right.setContentsMargins(20, 25, 20, 20)

        # 配置区 (容器，用于整体禁用)
        self.enc_cfg_area = QWidget()
        cfg_l = QVBoxLayout(self.enc_cfg_area)
        cfg_l.setContentsMargins(0, 0, 0, 0)

        cfg_l.addWidget(QLabel("设置密码:"))
        self.enc_pwd = QLineEdit();
        self.enc_pwd.setEchoMode(QLineEdit.Password);
        self.enc_pwd.setMinimumHeight(35)
        cfg_l.addWidget(self.enc_pwd)
        cfg_l.addSpacing(15)

        cfg_l.addWidget(QLabel("输出位置:"))
        path_l = QHBoxLayout()
        self.lbl_enc_path = QLineEdit("默认: 源文件位置");
        self.lbl_enc_path.setReadOnly(True)
        b_sel = QPushButton("选择");
        b_sel.clicked.connect(lambda: self.select_out_dir(True))
        b_rst = QPushButton("重置");
        b_rst.clicked.connect(lambda: self.reset_out_dir(True))
        path_l.addWidget(self.lbl_enc_path);
        path_l.addWidget(b_sel);
        path_l.addWidget(b_rst)
        cfg_l.addLayout(path_l)

        cfg_l.addSpacing(10)
        self.chk_name = QCheckBox("🔏 混淆文件名");
        self.chk_name.setChecked(True)
        self.chk_del = QCheckBox("⚠️ 完成后删除源文件")
        cfg_l.addWidget(self.chk_name);
        cfg_l.addWidget(self.chk_del)

        l_right.addWidget(self.enc_cfg_area)
        l_right.addStretch()

        # 状态区
        self.enc_status = QLabel("等待任务...")
        self.enc_pbar = QProgressBar()
        l_right.addWidget(self.enc_status);
        l_right.addWidget(self.enc_pbar)
        l_right.addSpacing(15)

        # 按钮切换逻辑：使用 StackedWidget 实现 "开始" 与 "暂停/停止" 的切换
        self.enc_btn_stack = QStackedWidget()

        # Page 0: 开始按钮
        self.btn_enc_run = QPushButton("🚀 开始加密")
        self.btn_enc_run.setObjectName("StartBtn")
        self.btn_enc_run.setMinimumHeight(50)
        self.btn_enc_run.clicked.connect(self.run_encrypt)
        self.enc_btn_stack.addWidget(self.btn_enc_run)

        # Page 1: 控制按钮组
        ctrl_widget = QWidget()
        ctrl_l = QHBoxLayout(ctrl_widget)
        ctrl_l.setContentsMargins(0, 0, 0, 0)
        self.btn_enc_pause = QPushButton("⏸️ 暂停")
        self.btn_enc_pause.setObjectName("PauseBtn")
        self.btn_enc_pause.setMinimumHeight(50)
        self.btn_enc_pause.clicked.connect(self.toggle_pause)

        self.btn_enc_stop = QPushButton("⏹️ 停止")
        self.btn_enc_stop.setObjectName("StopBtn")
        self.btn_enc_stop.setMinimumHeight(50)
        self.btn_enc_stop.clicked.connect(self.stop_task)

        ctrl_l.addWidget(self.btn_enc_pause)
        ctrl_l.addWidget(self.btn_enc_stop)
        self.enc_btn_stack.addWidget(ctrl_widget)

        # Page 2: 打开文件夹 (完成后显示)
        self.btn_enc_open = QPushButton("📂 打开输出文件夹")
        self.btn_enc_open.setMinimumHeight(50)
        self.btn_enc_open.clicked.connect(self.open_last_folder)
        self.enc_btn_stack.addWidget(self.btn_enc_open)

        l_right.addWidget(self.enc_btn_stack)

        layout.addWidget(left_grp, 6);
        layout.addWidget(right_grp, 4)
        self.tabs.addTab(tab, "🔒 加密工作台")

    # ================= 解密页 =================
    def _init_decrypt_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 30, 20, 20)

        left_grp = QGroupBox("1. 文件队列")
        l_left = QVBoxLayout(left_grp)
        l_left.setContentsMargins(15, 25, 15, 15)
        self.dec_list = DragDropListWidget()

        btn_l = QHBoxLayout()
        b_add = QPushButton("➕ 添加");
        b_add.clicked.connect(lambda: self.add_files(False))
        b_del = QPushButton("➖ 移除");
        b_del.clicked.connect(lambda: self.remove_sel(self.dec_list))
        b_clr = QPushButton("🗑️ 清空");
        b_clr.clicked.connect(self.dec_list.clear)
        btn_l.addWidget(b_add);
        btn_l.addWidget(b_del);
        btn_l.addWidget(b_clr)
        l_left.addWidget(self.dec_list);
        l_left.addLayout(btn_l)

        right_grp = QGroupBox("2. 解密配置")
        right_grp.setFixedWidth(400)
        l_right = QVBoxLayout(right_grp)
        l_right.setContentsMargins(20, 25, 20, 20)

        # 配置区
        self.dec_cfg_area = QWidget()
        cfg_l = QVBoxLayout(self.dec_cfg_area)
        cfg_l.setContentsMargins(0, 0, 0, 0)

        cfg_l.addWidget(QLabel("解密密码:"))
        self.dec_pwd = QLineEdit();
        self.dec_pwd.setEchoMode(QLineEdit.Password);
        self.dec_pwd.setMinimumHeight(35)
        cfg_l.addWidget(self.dec_pwd)
        cfg_l.addSpacing(15)

        cfg_l.addWidget(QLabel("输出位置:"))
        path_l = QHBoxLayout()
        self.lbl_dec_path = QLineEdit("默认: 源文件位置");
        self.lbl_dec_path.setReadOnly(True)
        b_sel = QPushButton("选择");
        b_sel.clicked.connect(lambda: self.select_out_dir(False))
        b_rst = QPushButton("重置");
        b_rst.clicked.connect(lambda: self.reset_out_dir(False))
        path_l.addWidget(self.lbl_dec_path);
        path_l.addWidget(b_sel);
        path_l.addWidget(b_rst)
        cfg_l.addLayout(path_l)

        cfg_l.addSpacing(10)
        self.chk_dec_del = QCheckBox("⚠️ 解密后清理加密包")
        cfg_l.addWidget(self.chk_dec_del)
        l_right.addWidget(self.dec_cfg_area)
        l_right.addStretch()

        self.dec_status = QLabel("等待任务...")
        self.dec_pbar = QProgressBar()
        l_right.addWidget(self.dec_status);
        l_right.addWidget(self.dec_pbar)
        l_right.addSpacing(15)

        # 按钮栈
        self.dec_btn_stack = QStackedWidget()

        self.btn_dec_run = QPushButton("🔓 开始解密")
        self.btn_dec_run.setObjectName("StartBtn")
        self.btn_dec_run.setMinimumHeight(50)
        self.btn_dec_run.setStyleSheet("background: #2e7d32;")
        self.btn_dec_run.clicked.connect(self.run_decrypt)
        self.dec_btn_stack.addWidget(self.btn_dec_run)

        ctrl_widget = QWidget()
        ctrl_l = QHBoxLayout(ctrl_widget);
        ctrl_l.setContentsMargins(0, 0, 0, 0)
        self.btn_dec_pause = QPushButton("⏸️ 暂停")
        self.btn_dec_pause.setObjectName("PauseBtn");
        self.btn_dec_pause.setMinimumHeight(50)
        self.btn_dec_pause.clicked.connect(self.toggle_pause)
        self.btn_dec_stop = QPushButton("⏹️ 停止")
        self.btn_dec_stop.setObjectName("StopBtn");
        self.btn_dec_stop.setMinimumHeight(50)
        self.btn_dec_stop.clicked.connect(self.stop_task)
        ctrl_l.addWidget(self.btn_dec_pause);
        ctrl_l.addWidget(self.btn_dec_stop)
        self.dec_btn_stack.addWidget(ctrl_widget)

        self.btn_dec_open = QPushButton("📂 打开输出文件夹")
        self.btn_dec_open.setMinimumHeight(50)
        self.btn_dec_open.clicked.connect(self.open_last_folder)
        self.dec_btn_stack.addWidget(self.btn_dec_open)

        l_right.addWidget(self.dec_btn_stack)

        layout.addWidget(left_grp, 6);
        layout.addWidget(right_grp, 4)
        self.tabs.addTab(tab, "🔓 解密工作台")

    # ================= 日志页 =================
    def _init_log_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(20, 30, 20, 20)

        self.log_txt = QTextEdit();
        self.log_txt.setReadOnly(True)
        self.log_txt.setStyleSheet(
            "background: #1e1e1e; border: 1px solid #444; color: #00ff00; font-family: Consolas;")
        l.addWidget(QLabel("📝 实时日志 (每秒自动刷新)"))
        l.addWidget(self.log_txt)
        self.tabs.addTab(tab, "日志")

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.load_log)
        self.log_timer.start(1000)

    # ================= 逻辑 =================
    def run_encrypt(self):
        self._start_task(True)

    def run_decrypt(self):
        self._start_task(False)

    def _start_task(self, is_encrypt):
        lst = self.enc_list if is_encrypt else self.dec_list
        pwd = self.enc_pwd if is_encrypt else self.dec_pwd
        files = [lst.item(i).text() for i in range(lst.count())]
        key = pwd.text()

        if not files or not key: return QMessageBox.warning(self, "警告", "请检查文件和密码")

        # 切换 UI 状态
        self.set_ui_processing(True, is_encrypt)

        path = self.custom_enc_path if is_encrypt else self.custom_dec_path

        self.worker = BatchWorkerThread(
            files, key, is_encrypt,
            encrypt_filename=self.chk_name.isChecked() if is_encrypt else False,
            custom_out_dir=path
        )

        lbl = self.enc_status if is_encrypt else self.dec_status
        pbar = self.enc_pbar if is_encrypt else self.dec_pbar

        self.worker.progress.connect(lambda m, s, t: (lbl.setText(m), pbar.setValue(t)))
        self.worker.log_update.connect(self.append_log)
        self.worker.finished.connect(lambda res: self.on_finish(res, is_encrypt))
        self.worker.start()

    def set_ui_processing(self, processing, is_encrypt):
        # 禁用配置区
        cfg = self.enc_cfg_area if is_encrypt else self.dec_cfg_area
        cfg.setEnabled(not processing)

        # 切换按钮栈: 0=开始, 1=控制, 2=打开
        stack = self.enc_btn_stack if is_encrypt else self.dec_btn_stack
        stack.setCurrentIndex(1 if processing else 0)

        # 重置暂停按钮
        self.is_paused = False
        btn_p = self.btn_enc_pause if is_encrypt else self.btn_dec_pause
        btn_p.setText("⏸️ 暂停")
        btn_p.setStyleSheet("background: #f09000;")

    def toggle_pause(self):
        if not self.worker: return
        is_enc = (self.tabs.currentIndex() == 0)
        btn = self.btn_enc_pause if is_enc else self.btn_dec_pause

        if self.is_paused:
            self.worker.resume()
            self.is_paused = False
            btn.setText("⏸️ 暂停")
            btn.setStyleSheet("background: #f09000;")
        else:
            self.worker.pause()
            self.is_paused = True
            btn.setText("▶️ 继续")
            btn.setStyleSheet("background: #23a559;")

    def stop_task(self):
        if self.worker:
            if self.is_paused: self.worker.resume()
            self.worker.stop()

    def on_finish(self, res, is_enc):
        # 切换到"打开文件夹"按钮
        stack = self.enc_btn_stack if is_enc else self.dec_btn_stack
        stack.setCurrentIndex(2)

        # 恢复配置区
        cfg = self.enc_cfg_area if is_enc else self.dec_cfg_area
        cfg.setEnabled(True)

        succ = len(res["success"])
        fail = len(res["fail"])

        if succ > 0:
            self.last_out_dir = os.path.dirname(res["success"][-1][1])

        del_chk = self.chk_del if is_enc else self.chk_dec_del
        if del_chk.isChecked():
            for src, _ in res["success"]:
                try:
                    os.remove(src)
                except:
                    pass

        QMessageBox.information(self, "完成", f"成功: {succ}\n失败: {fail}")

    # 辅助函数
    def append_log(self, msg):
        self.log_txt.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.log_txt.verticalScrollBar().setValue(self.log_txt.verticalScrollBar().maximum())

    def load_log(self):
        try:
            f = sorted(os.listdir(DIRS["LOGS"]))[-1]
            with open(os.path.join(DIRS["LOGS"], f), 'r', encoding='utf-8-sig') as file:
                c = file.read()
            if c != self.log_txt.toPlainText():
                sb = self.log_txt.verticalScrollBar()
                bot = sb.value() == sb.maximum()
                self.log_txt.setText(c)
                if bot: sb.setValue(sb.maximum())
        except:
            pass

    def select_out_dir(self, is_enc):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            if is_enc:
                self.custom_enc_path = d; self.lbl_enc_path.setText(d)
            else:
                self.custom_dec_path = d; self.lbl_dec_path.setText(d)

    def reset_out_dir(self, is_enc):
        if is_enc:
            self.custom_enc_path = None; self.lbl_enc_path.setText("默认: 源文件位置")
        else:
            self.custom_dec_path = None; self.lbl_dec_path.setText("默认: 源文件位置")

    def add_files(self, is_enc):
        flter = "All Files (*)" if is_enc else "Encrypted (*.enc)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", flter)
        t = self.enc_list if is_enc else self.dec_list
        if files: t.addItems(files)

    def remove_sel(self, t):
        for i in t.selectedItems(): t.takeItem(t.row(i))

    def open_last_folder(self):
        if self.last_out_dir and os.path.exists(self.last_out_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out_dir))
        else:
            QMessageBox.information(self, "提示", "尚未生成输出文件")