from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout, QLabel, QMessageBox
from core.auth import AuthService


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("用户鉴权")
        self.resize(300, 200)
        self.auth = AuthService()

        layout = QVBoxLayout(self)
        self.user_in = QLineEdit()
        self.user_in.setPlaceholderText("用户名")
        self.pass_in = QLineEdit()
        self.pass_in.setPlaceholderText("密码")
        self.pass_in.setEchoMode(QLineEdit.Password)

        btn = QPushButton("登录系统")
        btn.clicked.connect(self.check_login)

        layout.addWidget(QLabel("🔒 安全登录"))
        layout.addWidget(self.user_in)
        layout.addWidget(self.pass_in)
        layout.addWidget(btn)

    def check_login(self):
        if self.auth.login(self.user_in.text(), self.pass_in.text()):
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "鉴权失败")