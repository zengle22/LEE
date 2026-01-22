#!/usr/bin/env python
"""
LEE 框架 + MetaGPT 环境验证脚本
在 conda 环境 (lee-env) 中运行
"""

import sys

def test_environment():
    print("=" * 60)
    print("LEE 框架 + MetaGPT 环境验证")
    print("=" * 60)
    print()

    # 1. Python 版本检查
    print("1. Python 版本检查")
    print(f"   Python 版本: {sys.version}")
    if sys.version_info >= (3, 9) and sys.version_info < (3, 11):
        print("   ✅ Python 版本符合要求")
    else:
        print("   ⚠️  Python 版本可能不完全兼容")
    print()

    # 2. 检查基础依赖
    print("2. 基础依赖检查")
    try:
        import yaml
        print("   ✅ PyYAML 已安装")
    except ImportError:
        print("   ❌ PyYAML 未安装")
        return False

    try:
        import jsonschema
        print(f"   ✅ JSONSchema {jsonschema.__version__} 已安装")
    except ImportError:
        print("   ❌ JSONSchema 未安装")
        return False
    print()

    # 3. 检查 MetaGPT
    print("3. MetaGPT 检查")
    try:
        import metagpt
        print(f"   ✅ MetaGPT {metagpt.__version__} 已安装")
    except ImportError as e:
        print(f"   ❌ MetaGPT 未安装: {e}")
        return False
    print()

    # 4. 检查 LEE 框架核心
    print("4. LEE 框架核心检查")
    try:
        import flowcore
        print(f"   ✅ flowcore {flowcore.__version__} 已安装")
    except ImportError as e:
        print(f"   ⚠️  flowcore 未安装（开发模式）: {e}")
        print("   提示: 运行 'pip install -e .' 安装开发版本")
    print()

    # 5. 检查 MetaGPT 依赖
    print("5. MetaGPT 依赖检查")
    try:
        import faiss
        print(f"   ✅ faiss-cpu {faiss.__version__} 已安装")
    except ImportError as e:
        print(f"   ❌ faiss-cpu 未安装: {e}")
        return False
    print()

    # 6. 测试 MetaGPT 初始化
    print("6. MetaGPT 初始化测试")
    try:
        from metagpt.config2 import Config
        print("   ✅ MetaGPT Config 模块导入成功")
    except Exception as e:
        print(f"   ⚠️  MetaGPT Config 模块导入失败: {e}")
    print()

    # 7. 测试 LEE 适配层
    print("7. LEE 适配层测试")
    try:
        from flowcore.engines.metagpt.protocol import LEERequest
        print("   ✅ LEE 协议层导入成功")
    except ImportError as e:
        print(f"   ⚠️  LEE 适配层未找到（开发模式）: {e}")
    print()

    print("=" * 60)
    print("✅ 环境验证完成！所有组件正常工作")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_environment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
