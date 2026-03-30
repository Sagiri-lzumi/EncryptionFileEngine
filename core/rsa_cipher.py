import os
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from core.logger import sys_logger


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
    def _cleanup_partial_output(output_path):
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as exc:
                sys_logger.log(f"清理临时输出文件失败: {output_path} ({exc})", "warning")

    @staticmethod
    def _encrypt_filename(filename, aes_key, iv):
        """复用老系统的文件名加密逻辑"""
        from cryptography.hazmat.primitives import padding as sym_padding

        name_cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        name_enc = name_cipher.encryptor()
        name_pad = sym_padding.PKCS7(128).padder()

        fname_bytes = filename.encode('utf-8')
        enc_fname_data = name_enc.update(name_pad.update(fname_bytes)) + name_enc.update(
            name_pad.finalize()) + name_enc.finalize()
        return enc_fname_data

    @staticmethod
    def encrypt_file(file_path, output_path, public_key_path, callback=None):
        """使用公钥加密文件"""
        import struct
        from cryptography.hazmat.primitives import padding as sym_padding
        try:
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

            # 获取原始文件名并加密（复用老系统逻辑）
            original_filename = os.path.basename(file_path)
            enc_fname_data = RSAFileCipher._encrypt_filename(original_filename, aes_key, iv)

            # 用AES加密文件
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            padder = sym_padding.PKCS7(128).padder()

            file_size = os.path.getsize(file_path)
            processed = 0

            with open(file_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
                # 写入头部：加密的AES密钥长度(4) + 加密的AES密钥 + IV(16) + 文件名长度(4) + 加密的文件名
                f_out.write(len(encrypted_aes_key).to_bytes(4, 'big'))
                f_out.write(encrypted_aes_key)
                f_out.write(iv)
                f_out.write(struct.pack('>I', len(enc_fname_data)))
                f_out.write(enc_fname_data)

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
        except (OSError, ValueError) as exc:
            RSAFileCipher._cleanup_partial_output(output_path)
            sys_logger.log(f"RSA 文件加密失败: {file_path} ({exc})", "error")
            return False, f"加密失败: {exc}"
        except Exception as exc:
            RSAFileCipher._cleanup_partial_output(output_path)
            sys_logger.log(f"RSA 文件加密出现未预期异常: {file_path} ({exc})", "error")
            return False, f"加密失败: {exc}"

        return True, "加密成功"

    @staticmethod
    def _decrypt_filename(enc_fname_data, aes_key, iv):
        """复用老系统的文件名解密逻辑"""
        from cryptography.hazmat.primitives import padding as sym_padding

        name_dec = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend()).decryptor()
        name_unpad = sym_padding.PKCS7(128).unpadder()

        dec_name_bytes = name_dec.update(enc_fname_data) + name_dec.finalize()
        orig_name = (name_unpad.update(dec_name_bytes) + name_unpad.finalize()).decode('utf-8')
        return orig_name

    @staticmethod
    def decrypt_file(file_path, output_path, private_key_path, password, callback=None):
        """使用私钥解密文件"""
        from cryptography.hazmat.primitives import padding as sym_padding

        try:
            private_key = RSAKeyManager.load_private_key(private_key_path, password)
        except (ValueError, TypeError, UnsupportedAlgorithm, OSError) as exc:
            sys_logger.log(f"加载 RSA 私钥失败: {private_key_path} ({exc})", "error")
            return False, "私钥密码错误或私钥文件无效"

        try:
            with open(file_path, 'rb') as f_in:
                key_len_bytes = f_in.read(4)
                if len(key_len_bytes) != 4:
                    return False, "文件头损坏"

                key_len = int.from_bytes(key_len_bytes, 'big')
                encrypted_aes_key = f_in.read(key_len)
                iv = f_in.read(16)
                if len(encrypted_aes_key) != key_len or len(iv) != 16:
                    return False, "文件头损坏"

                try:
                    aes_key = private_key.decrypt(
                        encrypted_aes_key,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                except ValueError as exc:
                    sys_logger.log(f"RSA AES 密钥解封失败: {file_path} ({exc})", "warning")
                    return False, "密钥错误或文件损坏"

                # 读取并解密文件名（复用老系统逻辑）
                import struct
                fname_len_bytes = f_in.read(4)
                if len(fname_len_bytes) != 4:
                    return False, "文件名头损坏"
                fname_len = struct.unpack('>I', fname_len_bytes)[0]
                enc_fname_data = f_in.read(fname_len)

                try:
                    original_filename = RSAFileCipher._decrypt_filename(enc_fname_data, aes_key, iv)
                    # 使用解密出的原始文件名，保持在同一目录
                    output_dir = os.path.dirname(output_path) if os.path.dirname(output_path) else '.'
                    output_path = os.path.join(output_dir, original_filename)
                except (ValueError, UnicodeDecodeError) as exc:
                    sys_logger.log(f"文件名解密失败: {file_path} ({exc})", "warning")
                    return False, "密钥错误或文件名损坏"

                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                unpadder = sym_padding.PKCS7(128).unpadder()

                file_size = max(os.path.getsize(file_path) - 4 - key_len - 16 - 4 - fname_len, 1)
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
        except (OSError, ValueError) as exc:
            RSAFileCipher._cleanup_partial_output(output_path)
            sys_logger.log(f"RSA 文件解密失败: {file_path} ({exc})", "error")
            return False, f"解密失败: {exc}"
        except Exception as exc:
            RSAFileCipher._cleanup_partial_output(output_path)
            sys_logger.log(f"RSA 文件解密出现未预期异常: {file_path} ({exc})", "error")
            return False, f"解密失败: {exc}"

        return True, "解密成功", output_path
