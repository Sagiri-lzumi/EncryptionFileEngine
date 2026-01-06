import os
import struct
import uuid
import shutil
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class FileCipherEngine:

    def _get_smart_chunk_size(self, file_size):
        """根据文件大小智能调整分块大小"""
        if file_size < 100 * 1024 * 1024:
            return 1 * 1024 * 1024
        elif file_size < 2 * 1024 * 1024 * 1024:
            return 10 * 1024 * 1024
        else:
            return 64 * 1024 * 1024

    def process_file_direct(self, file_path, target_path, key_bytes, is_encrypt, encrypt_filename=False, callback=None,
                            controller=None):
        final_out_path = target_path

        try:
            if not os.path.exists(file_path):
                return False, "源文件不存在", ""

            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            file_size = os.path.getsize(file_path)
            chunk_size = self._get_smart_chunk_size(file_size)

            # ================= 加密模式 =================
            if is_encrypt:
                if encrypt_filename:
                    # 生成随机文件名
                    random_name = str(uuid.uuid4().hex)[:12] + ".enc"
                    final_out_path = os.path.join(target_dir, random_name)

                iv = os.urandom(16)
                cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                encryptor = cipher.encryptor()
                padder = padding.PKCS7(128).padder()

                original_filename = os.path.basename(file_path)

                # 加密文件名 Metadata
                name_cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                name_enc = name_cipher.encryptor()
                name_pad = padding.PKCS7(128).padder()

                fname_bytes = original_filename.encode('utf-8')
                enc_fname_data = name_enc.update(name_pad.update(fname_bytes)) + name_enc.update(
                    name_pad.finalize()) + name_enc.finalize()

                with open(file_path, 'rb') as f_in, open(final_out_path, 'wb') as f_out:
                    # 写入文件头: IV(16) + NameLen(4) + EncNameBytes(...) + OriginSize(8)
                    f_out.write(iv)
                    f_out.write(struct.pack('>I', len(enc_fname_data)))
                    f_out.write(enc_fname_data)
                    f_out.write(struct.pack('>Q', file_size))

                    processed = 0
                    while True:
                        if controller:
                            if controller.is_stop_requested(): raise InterruptedError("STOP")
                            controller.wait_if_paused()

                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            final = encryptor.update(padder.finalize()) + encryptor.finalize()
                            f_out.write(final)
                            break

                        f_out.write(encryptor.update(padder.update(chunk)))
                        processed += len(chunk)
                        if callback: callback(processed, file_size)

                return True, "加密成功", final_out_path

            # ================= 解密模式 =================
            else:
                with open(file_path, 'rb') as f_in:
                    # 1. 读取 IV
                    iv = f_in.read(16)
                    if len(iv) < 16: return False, "文件头损坏", ""

                    try:
                        # 2. 读取文件名长度
                        name_len_bytes = f_in.read(4)
                        if len(name_len_bytes) < 4: return False, "文件头损坏(Len)", ""
                        name_len = struct.unpack('>I', name_len_bytes)[0]
                        enc_fname_data = f_in.read(name_len)

                        # 3. 解密原始文件名
                        try:
                            name_dec = Cipher(algorithms.AES(key_bytes), modes.CBC(iv),
                                              backend=default_backend()).decryptor()
                            name_unpad = padding.PKCS7(128).unpadder()

                            dec_name_bytes = name_dec.update(enc_fname_data) + name_dec.finalize()
                            orig_name = (name_unpad.update(dec_name_bytes) + name_unpad.finalize()).decode('utf-8')
                        except:
                            return False, "密钥错误", ""

                        # 【核心】忽略传入的 target_path 文件名，强制恢复原名
                        final_out_path = os.path.join(target_dir, orig_name)

                        # 4. 读取原始大小 (跳过)
                        f_in.read(8)

                        # 5. 解密内容
                        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                        decryptor = cipher.decryptor()
                        unpadder = padding.PKCS7(128).unpadder()

                        header_size = 16 + 4 + name_len + 8
                        total_file_size = os.path.getsize(file_path)
                        data_size = total_file_size - header_size
                        if data_size <= 0: data_size = 1

                        processed = 0
                        with open(final_out_path, 'wb') as f_out:
                            while True:
                                if controller:
                                    if controller.is_stop_requested(): raise InterruptedError("STOP")
                                    controller.wait_if_paused()

                                chunk = f_in.read(chunk_size)
                                if not chunk:
                                    final = unpadder.update(decryptor.finalize()) + unpadder.finalize()
                                    f_out.write(final)
                                    break

                                f_out.write(unpadder.update(decryptor.update(chunk)))
                                processed += len(chunk)
                                if callback: callback(processed, data_size)

                    except ValueError:
                        return False, "数据损坏或填充错误", ""
                    except Exception as e:
                        return False, f"解密异常: {str(e)}", ""

                return True, "解密成功", final_out_path

        except InterruptedError:
            if os.path.exists(final_out_path):
                try: os.remove(final_out_path)
                except: pass
            return False, "用户停止", ""

        except Exception as e:
            if os.path.exists(final_out_path):
                try: os.remove(final_out_path)
                except: pass
            return False, str(e), ""