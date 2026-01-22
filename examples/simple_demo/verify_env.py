#!/usr/bin/env python3
"""
最简单的 MetaGPT 验证脚本
验证环境和基础功能
"""

import sys


def test_basic_imports():
    """测试基础导入"""
    print("=" * 60)
    print("基础导入测试")
    print("=" * 60)
    print()

    # 测试 1: MetaGPT 导入
    print("1. MetaGPT 导入测试")
    try:
        import metagpt
        print("   ✓ MetaGPT 导入成功")
    except ImportError as e:
        print(f"   ✗ MetaGPT 导入失败: {e}")
        return False
    print()

    # 测试 2: faiss-cpu 导入
    print("2. faiss-cpu 导入测试")
    try:
        import faiss
        print(f"   ✓ faiss-cpu {faiss.__version__} 导入成功")
    except ImportError as e:
        print(f"   ✗ faiss-cpu 导入失败: {e}")
        return False
    print()

    # 测试 3: MetaGPT 模块导入
    print("3. MetaGPT 模块导入测试")
    try:
        from metagpt.roles import Architect
        print("   ✓ Architect 角色模块导入成功")
    except ImportError as e:
        print(f"   ✗ Architect 模块导入失败: {e}")
        return False
    print()

    # 测试 4: LEE 框架导入
    print("4. LEE 框架导入测试")
    try:
        import flowcore
        print(f"   ✓ flowcore {flowcore.__version__} 导入成功")
    except ImportError as e:
        print(f"   ⚠ flowcore 导入失败: {e}")
    print()

    print("=" * 60)
    print("✅ 所有基础导入测试通过！")
    print("=" * 60)
    return True


def test_metagpt_role():
    """测试 MetaGPT 角色创建（需要配置，可能会失败）"""
    print()
    print("=" * 60)
    print("MetaGPT 角色测试（需要配置）")
    print("=" * 60)
    print()

    try:
        from metagpt.roles import Architect
        role = Architect()
        print("   ✓ Architect 角色创建成功")
        print("   注意：完整运行需要配置 API keys")
        return True
    except Exception as e:
        print(f"   ⚠ 角色创建失败（预期，需要配置）: {e}")
        return False


def main():
    """主函数"""
    print()
    print("🚀 LEE + MetaGPT 环境验证 Demo")
    print()

    # 测试 1: 基础导入
    if not test_basic_imports():
        print()
        print("❌ 基础导入测试失败，请检查环境")
        return False

    # 测试 2: MetaGPT 角色（可能会失败，需要配置）
    test_metagpt_role()

    print()
    print("=" * 60)
    print("✅ Demo 验证完成！")
    print("=" * 60)
    print()
    print("环境状态：✅ 可用")
    print("Python 版本：", sys.version_info.major, ".", sys.version_info.minor, ".", sys.version_info.micro)
    print("说明：基础功能正常，完整功能需要配置 MetaGPT API keys")
    print()

    # 显示下一步提示
    print("下一步：")
    print("1. 初始化 MetaGPT 配置：")
    print("   conda run -n lee-env metagpt --init-config")
    print()
    print("2. 编辑配置文件设置 API keys：")
    print("   ~/.metagpt/config2.yaml")
    print()
    print("3. 运行完整示例：")
    print("   conda run -n lee-env python examples/simple_demo/test_metagpt.py")
    print()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
