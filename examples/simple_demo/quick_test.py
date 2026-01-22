#!/usr/bin/env python3
"""
最简单的 MetaGPT 验证脚本 - 只验证基础导入
避免触发 Config 初始化
"""

import sys


def main():
    print("=" * 60)
    print("🚀 LEE + MetaGPT 环境快速验证")
    print("=" * 60)
    print()

    # 测试 1: MetaGPT 基础导入
    print("1. MetaGPT 基础导入")
    try:
        import metagpt
        print("   ✓ MetaGPT 模块导入成功")
    except ImportError as e:
        print(f"   ✗ 失败: {e}")
        return False
    print()

    # 测试 2: faiss-cpu
    print("2. faiss-cpu 验证")
    try:
        import faiss
        print(f"   ✓ faiss-cpu {faiss.__version__}")
    except ImportError as e:
        print(f"   ✗ 失败: {e}")
        return False
    print()

    # 测试 3: LEE 框架
    print("3. LEE 框架验证")
    try:
        import flowcore
        print(f"   ✓ flowcore {flowcore.__version__}")
    except ImportError as e:
        print(f"   ⚠  可选: {e}")
    print()

    # 测试 4: 不触发 Config 的简单操作
    print("4. MetaGPT 常量验证")
    try:
        from metagpt.const import WORKSPACE_ROOT, PROJECT_ROOT
        print(f"   ✓ WORKSPACE_ROOT: {WORKSPACE_ROOT}")
        print(f"   ✓ PROJECT_ROOT: {PROJECT_ROOT}")
    except Exception as e:
        print(f"   ⚠  可选: {e}")
    print()

    print("=" * 60)
    print("✅ 验证完成！")
    print("=" * 60)
    print()
    print("✅ 环境状态：可用")
    print(f"✅ Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"✅ MetaGPT: 已安装")
    print(f"✅ faiss-cpu: {faiss.__version__}")
    print()
    print("📝 说明:")
    print("  - 基础功能完全可用")
    print("  - MetaGPT Config 需要 API keys 配置")
    print("  - 运行 'metagpt --init-config' 初始化配置")
    print()
    print("🚀 下一步:")
    print("  1. 初始化配置: metagpt --init-config")
    print("  2. 配置 API keys: 编辑 ~/.metagpt/config2.yaml")
    print("  3. 运行示例: python -m metagpt.software_company")
    print()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
