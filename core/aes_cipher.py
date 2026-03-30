"""共享的 AES 加密工具类"""
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class AESCipher:
    """AES-256-CBC 加密工具类"""

    @staticmethod
    def generate_key() -> bytes:
        """生成 32 字节的 AES-256 密钥"""
        return os.urandom(32)

    @staticmethod
    def generate_iv() -> bytes:
        """生成 16 字节的 IV"""
        return os.urandom(16)

    @staticmethod
    def encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        AES-256-CBC 加密

        Args:
            plaintext: 明文数据
            key: 32 字节密钥
            iv: 16 字节 IV

        Returns:
            加密后的数据
        """
        # Padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()

        # 加密
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        return encryptor.update(padded_data) + encryptor.finalize()

    @staticmethod
    def decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        AES-256-CBC 解密

        Args:
            ciphertext: 密文数据
            key: 32 字节密钥
            iv: 16 字节 IV

        Returns:
            解密后的数据
        """
        # 解密
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Unpadding
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded_data) + unpadder.finalize()
