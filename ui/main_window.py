import os
import time
import threading
import hashlib
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QPushButton, QLabel, QFileDialog,
                               QGroupBox, QTextEdit, QLineEdit, QProgressBar,
                               QMessageBox, QListWidget, QAbstractItemView,
                               QFrame, QStackedWidget, QApplication, QCheckBox)
from PySide6.QtCore import QThread, Signal, Qt, QUrl, QTimer, QMutex, QObject
from PySide6.QtGui import QDesktopServices, QPainter, QColor, QAction

# ================= 导入检测 =================
# [修改说明] 移除了 try-except 保护，直接强制导入。
# 这样如果 core.logger 或 config 有错误，程序会直接报错提示，
# 而不是切换到模拟模式导致日志写不进去。
from config import DIRS
from core.file_cipher import FileCipherEngine
from core.logger import sys_logger


# ================= 样式表 (Apple/Telegram 现代风格) =================

DARK_THEME = """
/* === 全局基调：Telegram 夜间蓝灰 === */
QMainWindow, QWidget { 
    background-color: #1c1c1e; /* Apple Dark Background */
    color: #ffffff; 
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 10pt;
    selection-background-color: #0a84ff;
}

/* === 顶部栏：毛玻璃模拟 === */
QFrame#TopBar {
    background-color: rgba(44, 44, 46, 0.8); /* 半透明深灰 */
    border-bottom: 1px solid rgba(84, 84, 88, 0.6); /* 极细分割线 */
}
QLabel { color: #ffffff; }

/* === 分组框：去边框，纯色块卡片 === */
QGroupBox { 
    border: none; /* 去掉边框 */
    border-radius: 12px; 
    margin-top: 28px; /* 留出标题空间 */
    background-color: #2c2c2e; /* Apple Secondary System Fill */
    padding-top: 20px;
}
QGroupBox::title { 
    subcontrol-origin: margin; 
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px; 
    color: #8e8e93; /* Apple Secondary Label Color */
    font-weight: 600;
    font-size: 10pt;
    background-color: transparent;
}

/* === 文件列表：iOS 风格 === */
QListWidget { 
    background-color: rgba(0, 0, 0, 0.2); /* 微黑背景，增加深度 */
    border: none;
    border-radius: 10px; 
    outline: none; /* 去掉选中时的虚线框 */
    padding: 5px;
}
QListWidget::item {
    height: 36px;
    padding-left: 10px;
    border-radius: 8px;
    margin-bottom: 2px;
    color: #dddddd;
}
/* 选中状态：模仿 macOS 高亮 */
QListWidget::item:selected {
    background-color: #0a84ff; /* iOS Blue */
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: rgba(255, 255, 255, 0.08); /* 微弱白光 */
}

/* === 输入框：扁平化 === */
QLineEdit, QTextEdit { 
    background-color: rgba(0, 0, 0, 0.2); 
    border: 1px solid transparent; 
    border-radius: 8px; 
    color: #ffffff; 
    padding: 8px 10px;
}
QLineEdit:focus, QTextEdit:focus { 
    background-color: rgba(0, 0, 0, 0.4);
    border: 1px solid #0a84ff; /* 聚焦时才显示蓝色边框 */
}

/* === 普通按钮：幽灵按钮 (Ghost Button) === */
QPushButton { 
    background-color: rgba(255, 255, 255, 0.08); /* 只有微弱的底色 */
    color: #ffffff; 
    border: none; 
    padding: 8px 16px; 
    border-radius: 8px; 
    font-weight: 500;
}
QPushButton:hover { 
    background-color: rgba(255, 255, 255, 0.15); /* 悬停变亮 */
}
QPushButton:pressed { 
    background-color: rgba(255, 255, 255, 0.05); 
}

/* === 核心按钮：iOS 纯蓝 === */
QPushButton[class="primary"] { 
    background-color: #0a84ff; 
    color: #ffffff;
    font-weight: 600;
    font-size: 11pt;
}
QPushButton[class="primary"]:hover { 
    background-color: #0077ed; /* 稍深一点 */
}
QPushButton[class="primary"]:pressed { 
    background-color: #006edb; 
}

/* === 危险按钮：iOS 纯红 === */
QPushButton[class="danger"] { 
    background-color: rgba(255, 69, 58, 0.15); /* 半透明红底 */
    color: #ff453a; 
}
QPushButton[class="danger"]:hover { 
    background-color: #ff453a; 
    color: #ffffff;
}

/* === 进度条：超细 === */
QProgressBar { 
    background-color: rgba(255, 255, 255, 0.1); 
    border: none; 
    height: 6px; /* 极细线条 */
    border-radius: 3px; 
}
QProgressBar::chunk { 
    background-color: #0a84ff; 
    border-radius: 3px; 
}

/* === 选项卡：底部导航风格 === */
QTabWidget::pane { border: none; }
QTabBar::tab { 
    background: transparent; 
    color: #8e8e93; 
    padding: 10px 20px; 
    font-size: 11pt; 
    font-weight: 600;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { 
    color: #0a84ff; 
    border-bottom: 2px solid #0a84ff; 
}
QTabBar::tab:hover { color: #ffffff; }
"""

LIGHT_THEME = """
/* === 全局基调：Apple System Light === */
QMainWindow, QWidget { 
    background-color: #f2f2f7; /* Apple System Gray 6 */
    color: #000000; 
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 10pt;
}

/* === 顶部栏 === */
QFrame#TopBar {
    background-color: rgba(255, 255, 255, 0.7); /* 磨砂白 */
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
QLabel { color: #000000; }

/* === 分组框：纯白卡片，轻微投影效果 === */
QGroupBox { 
    border: 1px solid rgba(0,0,0,0.03); /* 极淡边框替代阴影 */
    border-radius: 12px; 
    margin-top: 28px; 
    background-color: #ffffff; 
    padding-top: 20px;
}
QGroupBox::title { 
    subcontrol-origin: margin; 
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px; 
    color: #8e8e93; 
    font-weight: 600;
    font-size: 10pt;
    background-color: transparent;
}

/* === 文件列表 === */
QListWidget { 
    background-color: #f2f2f7; /* 内部浅灰，形成对比 */
    border: none;
    border-radius: 10px; 
    outline: none;
    padding: 5px;
}
QListWidget::item {
    height: 36px;
    padding-left: 10px;
    border-radius: 8px;
    margin-bottom: 2px;
    color: #1c1c1e;
}
QListWidget::item:selected {
    background-color: #007aff; 
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: rgba(0, 0, 0, 0.04);
}

/* === 输入框 === */
QLineEdit, QTextEdit { 
    background-color: #f2f2f7; 
    border: 1px solid transparent; 
    border-radius: 8px; 
    color: #1c1c1e; 
    padding: 8px 10px;
}
QLineEdit:focus, QTextEdit:focus { 
    background-color: #ffffff; 
    border: 1px solid #007aff;
}

/* === 普通按钮 === */
QPushButton { 
    background-color: #ffffff; 
    color: #000000; 
    border: 1px solid rgba(0,0,0,0.1); /* 极细边框 */
    padding: 8px 16px; 
    border-radius: 8px; 
    font-weight: 500;
}
QPushButton:hover { 
    background-color: #f9f9f9; 
    border-color: rgba(0,0,0,0.2);
}
QPushButton:pressed { 
    background-color: #f0f0f0; 
}

/* === 核心按钮 === */
QPushButton[class="primary"] { 
    background-color: #007aff; 
    color: #ffffff;
    border: none;
    font-weight: 600;
    font-size: 11pt;
}
QPushButton[class="primary"]:hover { 
    background-color: #006bd6; 
}

/* === 危险按钮 === */
QPushButton[class="danger"] { 
    background-color: #fff2f2; 
    color: #ff3b30; 
    border: 1px solid #ffcccc;
}
QPushButton[class="danger"]:hover { 
    background-color: #ff3b30; 
    color: #ffffff;
    border: 1px solid #ff3b30;
}

/* === 进度条 === */
QProgressBar { 
    background-color: #e5e5ea; 
    border: none; 
    height: 6px; 
    border-radius: 3px; 
}
QProgressBar::chunk { 
    background-color: #007aff; 
    border-radius: 3px; 
}

/* === 选项卡 === */
QTabWidget::pane { border: none; }
QTabBar::tab { 
    background: transparent; 
    color: #8e8e93; 
    padding: 10px 20px; 
    font-size: 11pt; 
    font-weight: 600;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { 
    color: #007aff; 
    border-bottom: 2px solid #007aff; 
}
QTabBar::tab:hover { color: #000000; }
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


# ================= [新增] 跨进程任务包装器 (放在类外面) =================
# 这个函数会在独立的进程中运行，不能直接访问 Qt 控件
def task_wrapper(file_path, out_dir, key_bytes, is_enc, enc_name, queue, stop_event, pause_event):
    from core.file_cipher import FileCipherEngine
    import time

    # 1. 定义兼容多进程的控制器
    class MPController:
        def is_stop_requested(self):
            return stop_event.is_set()

        def wait_if_paused(self):
            pause_event.wait()  # 阻塞直到 set()

    # 2. 定义回调，通过 Queue 发送进度回主进程
    # 为了减少通信开销，可以做一个简单的节流
    last_update = 0

    def mp_callback(current, total):
        nonlocal last_update
        now = time.time()
        # 每 0.05秒 或 完成时发送一次，减少 IPC 压力
        if now - last_update > 0.05 or current == total:
            queue.put(("PROGRESS", file_path, current, total))
            last_update = now

    # 3. 执行核心逻辑
    engine = FileCipherEngine()
    try:
        # 开始处理
        queue.put(("START", file_path, os.path.getsize(file_path)))

        success, msg, out_path = engine.process_file(
            file_path, out_dir, key_bytes, is_enc, enc_name,
            callback=mp_callback,
            controller=MPController()
        )
        return (file_path, success, msg, out_path)
    except Exception as e:
        return (file_path, False, str(e), "")


# ================= 辅助函数：文件大小格式化 =================
def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


# ================= 核心：工作线程 (多进程火力全开版) =================
class BatchWorkerThread(QThread):
    sig_progress = Signal(str, int)  # 状态栏文本, 总进度百分比
    sig_log = Signal(str)  # 日志
    sig_finished = Signal(dict)  # 完成

    def __init__(self, files, key, is_encrypt, encrypt_filename=False, custom_out_dir=None):
        super().__init__()
        self.files = files
        self.key = key
        self.is_enc = is_encrypt
        self.enc_name = encrypt_filename
        self.custom_out = custom_out_dir

        # 使用 Manager 来管理跨进程共享状态
        self.manager = multiprocessing.Manager()
        self.queue = self.manager.Queue()
        self.stop_event = self.manager.Event()
        self.pause_event = self.manager.Event()
        self.pause_event.set()  # 默认非暂停状态

        self.total_bytes = 0
        self.processed_bytes_map = {}  # 记录每个文件的已处理字节

        self._is_running = True

    def pause(self):
        self.pause_event.clear()  # 所有子进程会在 wait() 处阻塞

    def resume(self):
        self.pause_event.set()  # 唤醒所有子进程

    def stop(self):
        self.stop_event.set()
        self._is_running = False

    def run(self):
        key_bytes = hashlib.sha256(self.key.encode()).digest()
        results = {"success": [], "fail": []}

        # 1. 扫描与计算总任务量
        valid_files = []
        self.total_bytes = 0
        self.processed_bytes_map = {}

        self.sig_log.emit("--- 正在根据 CPU 核心数分配计算资源 ---")

        for f in self.files:
            if os.path.exists(f):
                s = os.path.getsize(f)
                self.total_bytes += s
                valid_files.append(f)
                self.processed_bytes_map[f] = 0
            else:
                results["fail"].append((f, "文件不存在"))

        if not valid_files:
            self.sig_finished.emit(results)
            return

        if self.total_bytes == 0: self.total_bytes = 1

        # 2. 启动多进程池
        # os.cpu_count() 获取物理核心数，通常直接跑满
        max_workers = os.cpu_count()
        # 如果文件少，不要开启过多进程浪费资源
        real_workers = min(max_workers, len(valid_files))

        action = "加密" if self.is_enc else "解密"
        self.sig_log.emit(
            f" [多核] 启动 {real_workers} 个并行核心处理 {len(valid_files)} 个文件 (总计 {format_size(self.total_bytes)})")

        with ProcessPoolExecutor(max_workers=real_workers) as executor:
            futures = []

            # 提交任务
            for f_path in valid_files:
                out_dir = self.custom_out if (self.custom_out and os.path.exists(self.custom_out)) else os.path.dirname(
                    f_path)

                # 注意：传递给子进程的参数必须是可序列化的 (Picklable)
                fut = executor.submit(
                    task_wrapper,  # 顶层函数
                    f_path, out_dir, key_bytes, self.is_enc, self.enc_name,
                    self.queue, self.stop_event, self.pause_event
                )
                futures.append(fut)

            # 3. 监听消息队列 (主线程充当监控中心)
            # 我们不使用 as_completed 阻塞等待，而是循环检查 queue 更新 UI
            finished_count = 0
            total_count = len(valid_files)

            while finished_count < total_count and self._is_running:
                # 尝试从队列获取消息，非阻塞或短超时
                try:
                    while not self.queue.empty():
                        msg_type, *data = self.queue.get_nowait()

                        if msg_type == "PROGRESS":
                            # data: [file_path, current, total]
                            f_path, curr, _ = data
                            self.processed_bytes_map[f_path] = curr

                        elif msg_type == "START":
                            # data: [file_path, size]
                            pass  # 可选：显示正在开始处理某文件

                    # 计算总进度
                    global_processed = sum(self.processed_bytes_map.values())
                    pct = int((global_processed / self.total_bytes) * 100)
                    self.sig_progress.emit(f"多核并行计算中... {pct}%", pct)

                except:
                    pass

                # 检查任务完成情况
                # 这里我们需要轮询 futures 的状态
                # 为了不阻塞 UI 更新，这里稍微 sleep 一下
                QThread.msleep(50)

                # 统计已完成的 Future
                # 注意：这种写法在任务极多时可能略有性能损耗，但在文件处理场景可接受
                done_futures = [f for f in futures if f.done()]
                if len(done_futures) > finished_count:
                    # 有新任务完成了
                    for f in done_futures:
                        if getattr(f, '_handled', False): continue
                        f._handled = True  # 标记已处理
                        finished_count += 1

                        try:
                            # 获取 task_wrapper 的返回值
                            f_path, success, msg, out_path = f.result()
                            fname = os.path.basename(f_path)
                            fsize = format_size(os.path.getsize(f_path)) if os.path.exists(f_path) else "?"

                            if success:
                                results["success"].append((f_path, out_path))
                                out_name = os.path.basename(out_path)
                                self.sig_log.emit(f" [核心完成] {fname} ({fsize}) -> {out_name}")
                            else:
                                if msg == "用户停止":  # 这里通常不会触发，因为直接 kill flag 了
                                    pass
                                else:
                                    results["fail"].append((f_path, msg))
                                    self.sig_log.emit(f" [失败] {fname} | {msg}")
                        except Exception as e:
                            self.sig_log.emit(f" [进程崩溃] {e}")

            # 4. 循环结束 (完成或停止)
            if not self._is_running:
                # 如果是强制停止，立即终止所有子进程
                executor.shutdown(wait=False, cancel_futures=True)
                self.sig_log.emit(" 用户强制终止所有并行进程")

        final_msg = "处理完成" if self._is_running else "任务已终止"
        self.sig_progress.emit(final_msg, 100 if self._is_running else 0)
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

        # 1. 顶部状态栏 - 高度 64px
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(64)
        self.top_bar.setObjectName("TopBar")

        hl = QHBoxLayout(self.top_bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(20)  # 增加间距

        self.lbl_title = QLabel("安全加密引擎内核")
        # 苹果风字体设置：更细、更干净
        self.lbl_title.setStyleSheet(
            "font-family: 'Segoe UI', 'Microsoft YaHei'; font-weight: 600; font-size: 13pt; letter-spacing: 1px;")
        hl.addWidget(self.lbl_title)

        # 增加一个弹簧，把按钮顶到右边
        hl.addStretch()

        self.btn_theme = QPushButton("外观模式")
        self.btn_theme.setFixedSize(100, 36)
        self.btn_theme.setCursor(Qt.PointingHandCursor)
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

        grp = QGroupBox("系统运行日志（提示：历史日志可在Logs文件夹下查找）")
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
        if not self.worker: return
        # 获取 worker 正在执行的任务类型 (True=加密, False=解密)
        is_enc_task = self.worker.is_enc
        # 锁定目标 UI，不随用户点击选项卡而改变
        ui = self.ui_enc if is_enc_task else self.ui_dec
        ui["status"].setText(text)
        ui["pbar"].setValue(val)

    def append_log(self, text):
        # 获取当前时间，包含微秒，并截取前3位作为毫秒
        # 格式示例: 10:30:45.123
        t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = "#a0a0a0" if self.is_dark else "#666"
        # 使用 HTML 渲染颜色，让时间戳稍微暗一点，突出日志内容
        self.txt_log.append(f"<span style='color:{color}'>[{t}]</span> {text}")
        # 同步写入到系统日志文件
        sys_logger.log(text)

    def action_toggle_pause(self):
        if not self.worker: return
        # [修复] 同样根据 worker 的实际任务类型来决定操作哪个 UI 的按钮
        is_enc_task = self.worker.is_enc
        ui = self.ui_enc if is_enc_task else self.ui_dec
        if self.is_paused:
            self.worker.resume()
            self.is_paused = False
            ui["btn_pause"].setText("挂起任务")
            ui["status"].setText("正在处理...")  # 恢复状态文本
        else:
            self.worker.pause()
            self.is_paused = True
            ui["btn_pause"].setText("继续任务")
            ui["status"].setText("任务已挂起 (等待继续)")

    def action_stop_task(self):
        if self.worker:
            # 如果处于暂停状态，先恢复再停止，避免子进程卡死
            if self.is_paused:
                self.worker.resume()
            self.worker.stop()
            # 记录日志
            task_type = "加密" if self.worker.is_enc else "解密"
            self.append_log(f" 用户请求强行终止 {task_type} 任务...")

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