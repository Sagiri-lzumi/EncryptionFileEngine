import base64
import hashlib
from Crypto.Cipher import AES, DES, ARC4, DES3
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


class TextCipher:
    @staticmethod
    def _get_key(user_key, length):
        return hashlib.sha256(user_key.encode()).digest()[:length]

    @staticmethod
    def encrypt(text, algo, key_str):
        data = text.encode('utf-8')

        if algo == "AES":
            key = TextCipher._get_key(key_str, 32)
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
            key = TextCipher._get_key(key_str, 24)
            iv = get_random_bytes(8)
            cipher = DES3.new(key, DES3.MODE_CBC, iv)
            ct = cipher.encrypt(pad(data, DES3.block_size))
            return base64.b64encode(iv + ct).decode()

        elif algo == "RC4":
            key = TextCipher._get_key(key_str, 16)
            cipher = ARC4.new(key)
            ct = cipher.encrypt(data)
            return base64.b64encode(ct).decode()

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