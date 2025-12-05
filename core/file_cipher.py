import os
import struct
import uuid
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class FileCipherEngine:

    def _get_smart_chunk_size(self, file_size):
        # 针对大文件优化缓冲区，减少 I/O 次数
        if file_size < 100 * 1024 * 1024:
            return 1 * 1024 * 1024  # <100MB: 1MB
        elif file_size < 2 * 1024 * 1024 * 1024:
            return 10 * 1024 * 1024  # <2GB: 10MB
        else:
            return 64 * 1024 * 1024  # >2GB: 64MB (极大提升大文件速度)

    def process_file(self, file_path, output_dir, key_bytes, is_encrypt, encrypt_filename=False, callback=None,
                     controller=None):
        try:
            if not os.path.exists(file_path): return False, "文件不存在", ""

            file_size = os.path.getsize(file_path)
            chunk_size = self._get_smart_chunk_size(file_size)

            # ================= 加密逻辑 =================
            if is_encrypt:
                iv = os.urandom(16)
                cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                encryptor = cipher.encryptor()
                padder_content = padding.PKCS7(128).padder()

                original_filename = os.path.basename(file_path)

                # 文件名加密
                name_enc = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend()).encryptor()
                name_pad = padding.PKCS7(128).padder()
                fname_bytes = original_filename.encode('utf-8')
                enc_fname = name_enc.update(name_pad.update(fname_bytes)) + name_enc.update(
                    name_pad.finalize()) + name_enc.finalize()

                if encrypt_filename:
                    random_name = str(uuid.uuid4().hex)[:12]
                    output_path = os.path.join(output_dir, f"{random_name}.enc")
                else:
                    output_path = os.path.join(output_dir, f"{original_filename}.enc")

                try:
                    with open(file_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
                        f_out.write(iv)
                        f_out.write(struct.pack('>I', len(enc_fname)))
                        f_out.write(enc_fname)
                        f_out.write(struct.pack('>Q', file_size))

                        processed = 0
                        while True:
                            # [关键] 检查暂停/停止
                            if controller:
                                if controller.is_stop_requested(): raise InterruptedError("STOP")
                                controller.wait_if_paused()  # 暂停卡点

                            chunk = f_in.read(chunk_size)
                            if not chunk:
                                final = encryptor.update(padder_content.finalize()) + encryptor.finalize()
                                f_out.write(final)
                                break

                            f_out.write(encryptor.update(padder_content.update(chunk)))

                            processed += len(chunk)
                            # [关键] 实时回调
                            if callback: callback(processed, file_size)

                    return True, "加密成功", output_path

                except InterruptedError:
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except:
                            pass
                    return False, "用户停止", ""

            # ================= 解密逻辑 =================
            else:
                try:
                    with open(file_path, 'rb') as f_in:
                        iv = f_in.read(16)
                        if len(iv) < 16: return False, "文件头损坏", ""
                        name_len = struct.unpack('>I', f_in.read(4))[0]
                        enc_fname = f_in.read(name_len)

                        try:
                            name_dec = Cipher(algorithms.AES(key_bytes), modes.CBC(iv),
                                              backend=default_backend()).decryptor()
                            name_unpad = padding.PKCS7(128).unpadder()
                            dec_name = name_dec.update(enc_fname) + name_dec.finalize()
                            orig_name = (name_unpad.update(dec_name) + name_unpad.finalize()).decode('utf-8')
                        except:
                            return False, "密码错误", ""

                        output_path = os.path.join(output_dir, orig_name)
                        file_size = struct.unpack('>Q', f_in.read(8))[0]

                        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                        decryptor = cipher.decryptor()
                        unpadder_content = padding.PKCS7(128).unpadder()

                        header_size = 16 + 4 + name_len + 8
                        processed = 0
                        # 估算实际内容大小
                        total_bytes = os.path.getsize(file_path) - header_size
                        if total_bytes <= 0: total_bytes = 1

                        with open(output_path, 'wb') as f_out:
                            while True:
                                if controller:
                                    if controller.is_stop_requested(): raise InterruptedError("STOP")
                                    controller.wait_if_paused()

                                chunk = f_in.read(chunk_size)
                                if not chunk:
                                    final = unpadder_content.update(decryptor.finalize()) + unpadder_content.finalize()
                                    f_out.write(final)
                                    break

                                f_out.write(unpadder_content.update(decryptor.update(chunk)))
                                processed += len(chunk)
                                if callback: callback(processed, total_bytes)

                    return True, "解密成功", output_path

                except InterruptedError:
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except:
                            pass
                    return False, "用户停止", ""

        except Exception as e:
            return False, str(e), ""