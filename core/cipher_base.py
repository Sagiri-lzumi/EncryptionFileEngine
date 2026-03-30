"""加密基类 - 定义统一的加密接口"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Callable


class CipherBase(ABC):
    """所有加密类的抽象基类"""

    @abstractmethod
    def encrypt(self, data: bytes, **kwargs) -> Tuple[bool, str, bytes]:
        """
        加密数据

        Args:
            data: 待加密的字节数据
            **kwargs: 额外参数

        Returns:
            (成功标志, 消息, 加密后的数据)
        """
        pass

    @abstractmethod
    def decrypt(self, data: bytes, **kwargs) -> Tuple[bool, str, bytes]:
        """
        解密数据

        Args:
            data: 待解密的字节数据
            **kwargs: 额外参数

        Returns:
            (成功标志, 消息, 解密后的数据)
        """
        pass


class FileCipherBase(CipherBase):
    """文件加密的抽象基类"""

    @abstractmethod
    def encrypt_file(
        self,
        input_path: str,
        output_path: str,
        key: bytes,
        callback: Optional[Callable] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        加密文件

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            key: 加密密钥
            callback: 进度回调函数
            **kwargs: 额外参数

        Returns:
            (成功标志, 消息)
        """
        pass

    @abstractmethod
    def decrypt_file(
        self,
        input_path: str,
        output_path: str,
        key: bytes,
        callback: Optional[Callable] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        解密文件

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            key: 解密密钥
            callback: 进度回调函数
            **kwargs: 额外参数

        Returns:
            (成功标志, 消息)
        """
        pass
