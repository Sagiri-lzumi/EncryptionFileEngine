# core/auth.py
import os
import json
from config import DIRS
from core.logger import sys_logger

class AuthService:
    def __init__(self):
        self.user_db = os.path.join(DIRS["KEYS"], "users.json")
        self._init_db()

    def _init_db(self):
        if not os.path.exists(self.user_db):
            with open(self.user_db, 'w') as f:
                json.dump({"admin": "123456"}, f) # 默认账户

    def login(self, username, password):
        with open(self.user_db, 'r') as f:
            users = json.load(f)
        if username in users and users[username] == password:
            sys_logger.log(f"用户 {username} 登录成功")
            return True
        sys_logger.log(f"用户 {username} 登录失败", "warning")
        return False