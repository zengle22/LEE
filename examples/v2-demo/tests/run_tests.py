"""
测试运行器 - 简单的测试运行脚本
"""

import sys
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# 导入测试
from test_demo import TestAddFunction

# 运行测试
test_instance = TestAddFunction()

tests = [
    ("test_add_positive_numbers", test_instance.test_add_positive_numbers),
    ("test_add_negative_numbers", test_instance.test_add_negative_numbers),
    ("test_add_mixed_numbers", test_instance.test_add_mixed_numbers),
    ("test_add_zero", test_instance.test_add_zero),
    ("test_add_large_numbers", test_instance.test_add_large_numbers),
]

passed = 0
failed = 0

for test_name, test_func in tests:
    try:
        test_func()
        print(f"✅ {test_name}")
        passed += 1
    except Exception as e:
        print(f"❌ {test_name}: {e}")
        failed += 1

print()
print(f"Results: {passed} passed, {failed} failed")

if failed > 0:
    sys.exit(1)
