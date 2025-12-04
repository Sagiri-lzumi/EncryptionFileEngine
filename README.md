# 🔒 Encryption Studio (Professional Edition)


**Encryption Studio** 是一个基于 Python 和 PySide6 开发的高级本地文件安全防御系统。它提供现代化的图形界面，支持大文件智能分块加密、文件名混淆、多线程批量处理以及多种文本加密算法。

> **注意**：本项目为离线版本，所有加解密操作均在本地完成，无数据上传风险。

## ✨ 核心功能 (Key Features)

* **⚡ 智能分块策略 (Smart Chunking)**
    * 无需手动设置，系统根据文件大小自动计算最佳分块（64KB - 10MB），在保证速度的同时极低占用内存，轻松处理 GB 级大文件。
* **🛡️ 企业级安全防护**
    * 采用 **AES-256 (CBC模式)** 工业级加密标准。
    * **文件名混淆 (Filename Obfuscation)**：加密后文件名变为随机乱码（如 `a1b2.enc`），解密时自动还原原始文件名，防止元数据泄露。
* **🚀 多线程批量处理**
    * 支持拖拽添加数百个文件，多线程队列执行，界面流畅不卡顿。
    * 支持任务队列管理（添加、移除、清空）。
* **📂 灵活的文件管理**
    * **原地加密/解密**：默认将结果生成在源文件同级目录，方便查找。
    * **源文件保护**：提供“完成后物理删除源文件”选项（默认关闭，需手动确认）。
    * **项目专有目录**：可选将文件统一归档至程序的 `EncryptedFile` / `DecryptedFile` 目录。
* **🎨 现代化 UI 设计**
    * IDE 风格的极速启动动画（1.5s 粒子光环）。
    * 深色模式 (Dark Theme)，扁平化控件，自适应布局。
* **📝 附带工具箱**
    * 集成文本加密工具：支持 AES, DES, 3DES, RC4, Base64, MD5。
    * 实时系统日志监控。

## 📸 界面预览 (Screenshots)

*(此处建议你上传截图后替换链接，例如：启动页、批量加密页、文本工具页)*

| 启动动画 | 批量加密 |
| :---: | :---: |
| ![Splash](https://via.placeholder.com/400x250?text=Splash+Screen) | ![Main UI](https://via.placeholder.com/400x250?text=Encryption+Tab) |

## 🛠️ 安装与运行 (Installation)

### 环境要求
* Python 3.8 或更高版本

### 1. 克隆项目
```bash
git clone [https://github.com/你的用户名/Encryption-Studio.git](https://github.com/你的用户名/Encryption-Studio.git)
cd Encryption-Studio