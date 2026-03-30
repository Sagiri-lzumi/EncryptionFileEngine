import base64
import binascii
import hashlib
import os
import struct

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.decrepit.ciphers import algorithms as decrepit_algorithms
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class TextCipher:
    MAGIC = b"TXC2"
    VERSION = 2
    DEFAULT_ITERATIONS = 200_000
    _ALGORITHM_IDS = {"AES": 1, "DES": 2, "3DES": 3, "RC4": 4}
    _ALGORITHM_NAMES = {value: key for key, value in _ALGORITHM_IDS.items()}

    def encrypt_text(self, text, password, algorithm="AES", iterations=DEFAULT_ITERATIONS):
        plaintext = self._ensure_bytes(text)
        algorithm_name = self._normalize_algorithm(algorithm)
        salt = self._random_bytes(16)
        iv = self._build_iv(algorithm_name)
        key = self._derive_key_pbkdf2(password, salt, algorithm_name, iterations)
        encrypted = self._encrypt_bytes(plaintext, key, algorithm_name, iv)
        header = struct.pack(
            ">4sBBIBB",
            self.MAGIC,
            self.VERSION,
            self._ALGORITHM_IDS[algorithm_name],
            iterations,
            len(salt),
            len(iv),
        )
        return base64.urlsafe_b64encode(header + salt + iv + encrypted).decode("ascii")

    def decrypt_text(self, token, password):
        payload = self._decode_payload(token)
        if payload.startswith(self.MAGIC):
            return self._decrypt_v2(payload, password)
        return self._decrypt_legacy_payload(payload, password)

    def encrypt_text_legacy(self, text, password, algorithm="AES"):
        plaintext = self._ensure_bytes(text)
        algorithm_name = self._normalize_algorithm(algorithm)
        iv = self._build_iv(algorithm_name)
        key = self._derive_key_legacy(password, algorithm_name)
        encrypted = self._encrypt_bytes(plaintext, key, algorithm_name, iv)
        header = bytes([self._ALGORITHM_IDS[algorithm_name], len(iv)])
        return base64.urlsafe_b64encode(header + iv + encrypted).decode("ascii")

    def encode_text(self, text, mode="Base64"):
        content = self._ensure_bytes(text)
        normalized = mode.upper()
        if normalized == "BASE64":
            return base64.b64encode(content).decode("ascii")
        if normalized == "MD5":
            return hashlib.md5(content).hexdigest()
        if normalized == "SHA256":
            return hashlib.sha256(content).hexdigest()
        raise ValueError(f"不支持的编码模式: {mode}")

    def encrypt(self, data, password, algorithm="AES", iterations=DEFAULT_ITERATIONS):
        return self.encrypt_text(data, password, algorithm, iterations)

    def decrypt(self, token, password):
        return self.decrypt_text(token, password)

    def _decrypt_v2(self, payload, password):
        try:
            magic, version, algorithm_id, iterations, salt_len, iv_len = struct.unpack(
                ">4sBBIBB", payload[:12]
            )
        except struct.error as exc:
            raise ValueError("密文头部损坏") from exc

        if magic != self.MAGIC or version != self.VERSION:
            raise ValueError("不支持的文本密文版本")

        offset = 12
        salt = payload[offset:offset + salt_len]
        offset += salt_len
        iv = payload[offset:offset + iv_len]
        ciphertext = payload[offset + iv_len:]

        if len(salt) != salt_len or len(iv) != iv_len:
            raise ValueError("密文头部或载荷损坏")

        algorithm_name = self._algorithm_name_from_id(algorithm_id)
        key = self._derive_key_pbkdf2(password, salt, algorithm_name, iterations)
        return self._decrypt_bytes(ciphertext, key, algorithm_name, iv)

    def _decrypt_legacy_payload(self, payload, password):
        if len(payload) < 2:
            raise ValueError("旧版密文头部损坏")

        algorithm_id = payload[0]
        iv_len = payload[1]
        iv = payload[2:2 + iv_len]
        ciphertext = payload[2 + iv_len:]

        if len(iv) != iv_len:
            raise ValueError("旧版密文内容损坏")

        algorithm_name = self._algorithm_name_from_id(algorithm_id)
        key = self._derive_key_legacy(password, algorithm_name)
        return self._decrypt_bytes(ciphertext, key, algorithm_name, iv)

    def _encrypt_bytes(self, data, key, algorithm_name, iv):
        cipher = self._build_cipher(algorithm_name, key, iv)
        encryptor = cipher.encryptor()
        if algorithm_name == "RC4":
            return encryptor.update(data) + encryptor.finalize()

        padder = padding.PKCS7(cipher.algorithm.block_size).padder()
        padded = padder.update(data) + padder.finalize()
        return encryptor.update(padded) + encryptor.finalize()

    def _decrypt_bytes(self, data, key, algorithm_name, iv):
        try:
            cipher = self._build_cipher(algorithm_name, key, iv)
            decryptor = cipher.decryptor()
            if algorithm_name == "RC4":
                plaintext = decryptor.update(data) + decryptor.finalize()
            else:
                padded = decryptor.update(data) + decryptor.finalize()
                unpadder = padding.PKCS7(cipher.algorithm.block_size).unpadder()
                plaintext = unpadder.update(padded) + unpadder.finalize()
            return plaintext.decode("utf-8")
        except (ValueError, UnicodeDecodeError, InvalidKey) as exc:
            raise ValueError("密码错误或密文损坏") from exc

    def _derive_key_legacy(self, password, algorithm_name):
        digest = hashlib.sha256(self._ensure_bytes(password)).digest()
        return self._adapt_key_for_algorithm(
            self._expand_key(digest, self._get_key_size(algorithm_name)),
            algorithm_name,
        )

    def _derive_key_pbkdf2(self, password, salt, algorithm_name, iterations):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self._get_key_size(algorithm_name),
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        return self._adapt_key_for_algorithm(
            kdf.derive(self._ensure_bytes(password)),
            algorithm_name,
        )

    def _build_cipher(self, algorithm_name, key, iv):
        if algorithm_name == "AES":
            return Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        if algorithm_name == "DES":
            return Cipher(decrepit_algorithms.TripleDES(key), modes.CBC(iv), backend=default_backend())
        if algorithm_name == "3DES":
            return Cipher(decrepit_algorithms.TripleDES(key), modes.CBC(iv), backend=default_backend())
        if algorithm_name == "RC4":
            return Cipher(decrepit_algorithms.ARC4(key), mode=None, backend=default_backend())
        raise ValueError(f"不支持的算法: {algorithm_name}")

    def _build_iv(self, algorithm_name):
        if algorithm_name == "AES":
            return self._random_bytes(16)
        if algorithm_name in {"DES", "3DES"}:
            return self._random_bytes(8)
        if algorithm_name == "RC4":
            return b""
        raise ValueError(f"不支持的算法: {algorithm_name}")

    def _get_key_size(self, algorithm_name):
        if algorithm_name == "AES":
            return 32
        if algorithm_name == "DES":
            return 8
        if algorithm_name == "3DES":
            return 24
        if algorithm_name == "RC4":
            return 16
        raise ValueError(f"不支持的算法: {algorithm_name}")

    def _expand_key(self, key_material, key_size):
        repeats = (key_size + len(key_material) - 1) // len(key_material)
        return (key_material * repeats)[:key_size]

    def _adapt_key_for_algorithm(self, key, algorithm_name):
        if algorithm_name == "DES":
            return key * 3
        return key

    def _algorithm_name_from_id(self, algorithm_id):
        try:
            return self._ALGORITHM_NAMES[algorithm_id]
        except KeyError as exc:
            raise ValueError("未知的算法标识") from exc

    def _normalize_algorithm(self, algorithm):
        normalized = algorithm.upper()
        if normalized not in self._ALGORITHM_IDS:
            raise ValueError(f"不支持的算法: {algorithm}")
        return normalized

    def _decode_payload(self, token):
        try:
            return base64.urlsafe_b64decode(self._ensure_bytes(token))
        except (binascii.Error, ValueError) as exc:
            raise ValueError("密文格式无效") from exc

    def _ensure_bytes(self, value):
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode("utf-8")
        raise TypeError("输入必须是 str 或 bytes")

    def _random_bytes(self, length):
        return os.urandom(length)
