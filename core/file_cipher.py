import os
import struct
import uuid
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class FileCipherEngine:

    def _get_smart_chunk_size(self, file_size):
        """内部智能匹配分块大小"""
        if file_size < 10 * 1024 * 1024:  # < 10MB
            return 64 * 1024  # 64KB (小文件极速)
        elif file_size < 1024 * 1024 * 1024:  # < 1GB
            return 1024 * 1024  # 1MB (标准)
        else:  # > 1GB
            return 10 * 1024 * 1024  # 10MB (大文件减少IO次数)

    def process_file(self, file_path, output_dir, key_bytes, is_encrypt, encrypt_filename=False, callback=None):
        """
        :param chunk_size: 已移除，改为内部自动计算
        """
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在", ""

            file_size = os.path.getsize(file_path)
            chunk_size = self._get_smart_chunk_size(file_size)  # ⚡ 自动匹配

            # ================= 加密逻辑 =================
            if is_encrypt:
                iv = os.urandom(16)
                cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                encryptor = cipher.encryptor()
                padder_content = padding.PKCS7(128).padder()

                # 1. 处理文件名
                original_filename = os.path.basename(file_path)

                # 加密文件名
                name_encryptor = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend()).encryptor()
                padder_name = padding.PKCS7(128).padder()
                filename_bytes = original_filename.encode('utf-8')
                enc_filename_bytes = name_encryptor.update(padder_name.update(filename_bytes)) + name_encryptor.update(
                    padder_name.finalize()) + name_encryptor.finalize()

                # 2. 决定输出文件名
                if encrypt_filename:
                    # 混淆文件名 (如: a1b2c3.enc)
                    random_name = str(uuid.uuid4().hex)[:12]
                    output_path = os.path.join(output_dir, f"{random_name}.enc")
                else:
                    # 保留原名 (如: report.pdf.enc)
                    output_path = os.path.join(output_dir, f"{original_filename}.enc")

                # 3. 写入
                with open(file_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
                    # Header: [IV 16] [NameLen 4] [EncName Var] [Size 8]
                    f_out.write(iv)
                    f_out.write(struct.pack('>I', len(enc_filename_bytes)))
                    f_out.write(enc_filename_bytes)
                    f_out.write(struct.pack('>Q', file_size))

                    processed = 0
                    while True:
                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            final = encryptor.update(padder_content.finalize()) + encryptor.finalize()
                            f_out.write(final)
                            break

                        data = padder_content.update(chunk)
                        f_out.write(encryptor.update(data))

                        processed += len(chunk)
                        if callback: callback(processed, file_size)

                return True, "加密成功", output_path

            # ================= 解密逻辑 =================
            else:
                with open(file_path, 'rb') as f_in:
                    # 1. 解析 Header
                    iv = f_in.read(16)
                    if len(iv) < 16: return False, "文件头损坏", ""

                    name_len_bytes = f_in.read(4)
                    if not name_len_bytes: return False, "文件头损坏", ""
                    name_len = struct.unpack('>I', name_len_bytes)[0]

                    enc_filename_bytes = f_in.read(name_len)

                    # 2. 解密文件名
                    try:
                        name_decryptor = Cipher(algorithms.AES(key_bytes), modes.CBC(iv),
                                                backend=default_backend()).decryptor()
                        unpadder_name = padding.PKCS7(128).unpadder()
                        dec_name_bytes = name_decryptor.update(enc_filename_bytes) + name_decryptor.finalize()
                        original_filename = (unpadder_name.update(dec_name_bytes) + unpadder_name.finalize()).decode(
                            'utf-8')
                    except:
                        return False, "密码错误或文件名解析失败", ""

                    output_path = os.path.join(output_dir, original_filename)

                    # 3. 解密内容
                    file_size = struct.unpack('>Q', f_in.read(8))[0]
                    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                    decryptor = cipher.decryptor()
                    unpadder_content = padding.PKCS7(128).unpadder()

                    # 计算Header总长
                    header_size = 16 + 4 + name_len + 8
                    current_total_size = os.path.getsize(file_path)

                    processed = 0
                    with open(output_path, 'wb') as f_out:
                        while True:
                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                final = unpadder_content.update(decryptor.finalize()) + unpadder_content.finalize()
                                f_out.write(final)
                                break

                            # 流式解密
                            f_out.write(unpadder_content.update(decryptor.update(chunk)))

                            processed += len(chunk)
                            if callback: callback(processed, current_total_size - header_size)

                return True, "解密成功", output_path

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"错误: {str(e)}", ""