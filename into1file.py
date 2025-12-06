import os


def merge_project_files():
    # 输出文件名
    output_file = 'all.txt'

    # 需要读取的根目录特定文件
    root_files = ['config.py', 'main.py']

    # 需要遍历的文件夹
    target_dirs = ['ui', 'core']

    # 获取脚本所在的当前根目录
    base_dir = os.getcwd()

    print(f"开始合并文件到 {output_file} ...")

    with open(output_file, 'w', encoding='utf-8') as outfile:

        # 1. 处理根目录下的特定文件
        for filename in root_files:
            file_path = os.path.join(base_dir, filename)
            if os.path.exists(file_path):
                write_file_content(outfile, filename, file_path)
            else:
                print(f"警告: 根目录下未找到 {filename}")
                outfile.write(f"\n# 警告: 未找到文件 {filename}\n")

        # 2. 处理指定文件夹下的所有 .py 文件
        for folder in target_dirs:
            folder_path = os.path.join(base_dir, folder)

            if not os.path.exists(folder_path):
                print(f"警告: 文件夹 {folder} 不存在")
                continue

            # os.walk 会递归遍历所有子目录
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith('.py'):
                        # 获取文件的完整路径
                        full_path = os.path.join(root, file)
                        # 获取相对路径（用于在 all.txt 中显示文件名，如 ui/menu.py）
                        relative_path = os.path.relpath(full_path, base_dir)

                        write_file_content(outfile, relative_path, full_path)

    print(f"完成！所有内容已写入 {output_file}")


def write_file_content(outfile, display_name, full_path):
    """读取文件内容并写入输出文件，带有分隔符"""
    try:
        # 添加醒目的分隔符，方便区分文件
        separator = f"\n{'=' * 60}\n文件路径: {display_name}\n{'=' * 60}\n"
        outfile.write(separator)

        with open(full_path, 'r', encoding='utf-8') as infile:
            content = infile.read()
            outfile.write(content)
            # 确保文件末尾有换行
            if not content.endswith('\n'):
                outfile.write('\n')

        print(f"已写入: {display_name}")

    except Exception as e:
        error_msg = f"# 读取文件 {display_name} 时出错: {str(e)}\n"
        outfile.write(error_msg)
        print(error_msg.strip())


if __name__ == '__main__':
    merge_project_files()