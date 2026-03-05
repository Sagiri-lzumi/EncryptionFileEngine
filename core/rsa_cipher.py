import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class RSAKeyManager:
    @staticmethod
    def generate_key_pair(password, key_name="rsa_key"):
        """生成RSA密钥对，用密码加密私钥"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        # 加密私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
        )

        # 公钥不加密
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    @staticmethod
    def load_private_key(key_path, password):
        """加载私钥"""
        with open(key_path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=password.encode(),
                backend=default_backend()
            )

    @staticmethod
    def load_public_key(key_path):
        """加载公钥"""
        with open(key_path, 'rb') as f:
            return serialization.load_pem_public_key(f.read(), backend=default_backend())


class RSAFileCipher:
    """RSA混合加密：用AES加密文件，用RSA加密AES密钥"""

    @staticmethod
    def encrypt_file(file_path, output_path, public_key_path, callback=None):
        """使用公钥加密文件"""
        from cryptography.hazmat.primitives import padding as sym_padding

        public_key = RSAKeyManager.load_public_key(public_key_path)

        # 生成随机AES密钥
        aes_key = os.urandom(32)
        iv = os.urandom(16)

        # 用RSA加密AES密钥
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 用AES加密文件
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = sym_padding.PKCS7(128).padder()

        file_size = os.path.getsize(file_path)
        processed = 0

        with open(file_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
            # 写入头部：加密的AES密钥长度(4) + 加密的AES密钥 + IV(16)
            f_out.write(len(encrypted_aes_key).to_bytes(4, 'big'))
            f_out.write(encrypted_aes_key)
            f_out.write(iv)

            # 加密文件内容
            while True:
                chunk = f_in.read(1024 * 1024)
                if not chunk:
                    final = encryptor.update(padder.finalize()) + encryptor.finalize()
                    f_out.write(final)
                    break
                f_out.write(encryptor.update(padder.update(chunk)))
                processed += len(chunk)
                if callback:
                    callback(processed, file_size)

        return True, "加密成功"

    @staticmethod
    def decrypt_file(file_path, output_path, private_key_path, password, callback=None):
        """使用私钥解密文件"""
        from cryptography.hazmat.primitives import padding as sym_padding

        try:
            private_key = RSAKeyManager.load_private_key(private_key_path, password)
        except:
            return False, "私钥密码错误"

        with open(file_path, 'rb') as f_in:
            # 读取加密的AES密钥
            key_len = int.from_bytes(f_in.read(4), 'big')
            encrypted_aes_key = f_in.read(key_len)
            iv = f_in.read(16)

            # 用RSA解密AES密钥
            try:
                aes_key = private_key.decrypt(
                    encrypted_aes_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
            except:
                return False, "密钥错误或文件损坏"

            # 用AES解密文件
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            unpadder = sym_padding.PKCS7(128).unpadder()

            file_size = os.path.getsize(file_path) - 4 - key_len - 16
            processed = 0

            with open(output_path, 'wb') as f_out:
                while True:
                    chunk = f_in.read(1024 * 1024)
                    if not chunk:
                        final = unpadder.update(decryptor.finalize()) + unpadder.finalize()
                        f_out.write(final)
                        break
                    f_out.write(unpadder.update(decryptor.update(chunk)))
                    processed += len(chunk)
                    if callback:
                        callback(processed, file_size)

        return True, "解密成功"
