"""
Root conftest.py - 解决 macOS .DS_Store 权限问题
"""
import os


def pytest_ignore_collect(collection_path, config):
    """跳过 .DS_Store 和其他非 Python 文件/目录"""
    name = os.path.basename(str(collection_path))
    # 跳过 .DS_Store、隐藏文件等
    if name == ".DS_Store" or name.startswith("."):
        return True
    return None
