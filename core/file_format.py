"""统一的加密文件格式定义"""
import struct
import json
from typing import Tuple, Optional


class FileFormat:
    """加密文件格式管理"""

    # V2 格式标识
    MAGIC_V2 = b"ENC2"
    VERSION_V2 = 2

    @staticmethod
    def is_v2_format(data: bytes) -> bool:
        """检查是否为 V2 格式"""
        return data[:4] == FileFormat.MAGIC_V2

    @staticmethod
    def pack_v2_header(iv: bytes, metadata: dict) -> bytes:
        """
        打包 V2 格式文件头

        格式: [MAGIC(4)] + [VERSION(1)] + [IV_LEN(1)] + [IV] + [METADATA_LEN(4)] + [METADATA]
        """
        iv_len = len(iv)
        metadata_bytes = json.dumps(metadata).encode('utf-8')
        metadata_len = len(metadata_bytes)

        header = struct.pack(
            f">4sBB{iv_len}sI{metadata_len}s",
            FileFormat.MAGIC_V2,
            FileFormat.VERSION_V2,
            iv_len,
            iv,
            metadata_len,
            metadata_bytes
        )
        return header

    @staticmethod
    def unpack_v2_header(data: bytes) -> Tuple[int, bytes, dict]:
        """
        解包 V2 格式文件头

        Returns:
            (版本号, IV, 元数据字典)
        """
        magic = data[:4]
        if magic != FileFormat.MAGIC_V2:
            raise ValueError("Invalid V2 format")

        version = data[4]
        iv_len = data[5]

        offset = 6
        iv = data[offset:offset + iv_len]
        offset += iv_len

        metadata_len = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4

        metadata_bytes = data[offset:offset + metadata_len]
        metadata = json.loads(metadata_bytes.decode('utf-8'))

        return version, iv, metadata
