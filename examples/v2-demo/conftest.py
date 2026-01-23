"""
Pytest 配置文件 - 限制扫描范围
"""
import os

# 限制 pytest 只扫描 tests 目录
collect_ignore = [
    "$RECYCLE.BIN",
    "node_modules",
    ".git",
    "__pycache__",
]
