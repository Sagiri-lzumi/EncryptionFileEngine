# core/text_cipher.py
import base64
import hashlib
from Crypto.Cipher import AES, DES, ARC4, DES3  # PyCryptodome for legacy algos
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


class TextCipher:
    """提供多种文本加密算法"""

    @staticmethod
    def _get_key(user_key, length):
        """将用户输入的字符串处理成特定长度的bytes"""
        return hashlib.sha256(user_key.encode()).digest()[:length]

    @staticmethod
    def encrypt(text, algo, key_str):
        data = text.encode('utf-8')

        if algo == "AES":
            key = TextCipher._get_key(key_str, 32)  # AES-256
            iv = get_random_bytes(16)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            ct = cipher.encrypt(pad(data, AES.block_size))
            return base64.b64encode(iv + ct).decode()

        elif algo == "DES":
            key = TextCipher._get_key(key_str, 8)
            iv = get_random_bytes(8)
            cipher = DES.new(key, DES.MODE_CBC, iv)
            ct = cipher.encrypt(pad(data, DES.block_size))
            return base64.b64encode(iv + ct).decode()

        elif algo == "TripleDES":
            key = TextCipher._get_key(key_str, 24)  # 16 or 24
            iv = get_random_bytes(8)
            cipher = DES3.new(key, DES3.MODE_CBC, iv)
            ct = cipher.encrypt(pad(data, DES3.block_size))
            return base64.b64encode(iv + ct).decode()

        elif algo == "RC4":
            key = TextCipher._get_key(key_str, 16)
            cipher = ARC4.new(key)
            ct = cipher.encrypt(data)
            return base64.b64encode(ct).decode()

        # Rabbit 在标准库中较少见，通常用 ChaCha20 代替，这里仅作结构示意或需特定库
        # 若必须 Rabbit，需确认安装了支持 Rabbit 的扩展库

        return "Algorithm not supported"

    @staticmethod
    def hash_encoding(text, method):
        data = text.encode()
        if method == "Base64":
            return base64.b64encode(data).decode()
        elif method == "MD5":
            return hashlib.md5(data).hexdigest()
        elif method == "SHA256":
            return hashlib.sha256(data).hexdigest()
        return ""