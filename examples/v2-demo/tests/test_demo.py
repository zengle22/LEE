"""
测试 demo.py 中的函数
"""

import sys
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

import pytest
from demo import add


class TestAddFunction:
    """测试 add 函数"""

    def test_add_positive_numbers(self):
        """测试正数相加"""
        assert add(2, 3) == 5

    def test_add_negative_numbers(self):
        """测试负数相加"""
        assert add(-2, -3) == -5

    def test_add_mixed_numbers(self):
        """测试正负数相加"""
        assert add(5, -3) == 2

    def test_add_zero(self):
        """测试加零"""
        assert add(5, 0) == 5
        assert add(0, 5) == 5
        assert add(0, 0) == 0

    def test_add_large_numbers(self):
        """测试大数相加"""
        assert add(1000000, 2000000) == 3000000
