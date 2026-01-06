import os
import time


def export_important_code():
    # 输出文件名
    output_filename = "all_code.txt"

    # 1. 【核心】只允许遍历这些文件夹
    ALLOWED_DIRS = {'core', 'ui'}

    # 2. 【核心】根目录下，只读取这些重要文件
    ALLOWED_ROOT_FILES = {'main.py', 'config.py'}

    # 3. 只读取 .py 文件
    VALID_EXTENSIONS = {'.py'}

    print(f"正在提取核心代码到 {output_filename} ...")

    try:
        with open(output_filename, 'w', encoding='utf-8') as out_f:
            # 写入头部
            out_f.write("=" * 50 + "\n")
            out_f.write(f"Encryption Studio 核心源码 (Core & UI)\n")
            out_f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            out_f.write("=" * 50 + "\n\n")

            # 开始遍历
            for root, dirs, files in os.walk("."):
                # 获取当前相对路径 (例如 "." 或 "core" 或 "ui/widgets")
                rel_path = os.path.relpath(root, ".")

                # === 关键筛选逻辑 ===

                # 情况A: 如果在项目根目录
                if rel_path == ".":
                    # 1. 强行修改 dirs，只保留 core 和 ui，其他文件夹(venv/build/logs)直接截断，不再进入
                    dirs[:] = [d for d in dirs if d in ALLOWED_DIRS]

                    # 2. 筛选文件：只处理 main.py 和 config.py
                    files_to_process = [f for f in files if f in ALLOWED_ROOT_FILES]

                # 情况B: 如果在 allowed_dirs (即 core 或 ui) 及其子目录内
                else:
                    # 此时允许所有 .py 文件
                    files_to_process = [f for f in files if os.path.splitext(f)[1] in VALID_EXTENSIONS]

                # === 开始写入 ===
                for file in files_to_process:
                    file_path = os.path.join(root, file)

                    out_f.write(f"\n{'=' * 20} FILE: {file_path} {'=' * 20}\n")

                    try:
                        with open(file_path, 'r', encoding='utf-8') as in_f:
                            out_f.write(in_f.read())
                    except Exception as e:
                        out_f.write(f"[Error reading file]: {e}")

                    out_f.write(f"\n{'=' * 20} END: {file_path} {'=' * 20}\n\n")
                    print(f"已提取: {file_path}")

        print(f"\n✅ 成功！核心代码已保存到: {os.path.abspath(output_filename)}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    export_important_code()