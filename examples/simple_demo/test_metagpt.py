#!/usr/bin/env python3
"""
简单的 MetaGPT demo
验证环境是否正常工作
"""

import asyncio
from metagpt.roles import Architect
from metagpt.config2 import Config
from metagpt.const import WORKSPACE_ROOT, PROJECT_ROOT


async def main():
    """主函数"""
    print("=" * 60)
    print("MetaGPT 简单 Demo")
    print("=" * 60)
    print()

    print("1. 初始化 MetaGPT 配置")
    print(f"   WORKSPACE_ROOT: {WORKSPACE_ROOT}")
    print(f"   PROJECT_ROOT: {PROJECT_ROOT}")
    print()

    print("2. 创建简单任务")
    # 使用一个简单的需求描述
    user_requirement = "创建一个简单的计算器应用，支持加、减、乘、除四则运算"
    print(f"   用户需求: {user_requirement}")
    print()

    print("3. 初始化架构师角色")
    # 创建架构师角色
    role = Architect()
    print("   ✓ 架构师角色已创建")
    print()

    print("4. 运行架构师生成设计")
    print("   正在生成设计文档...")
    print()

    try:
        # 运行架构师
        result = await role.run(user_requirement)
        print()
        print("=" * 60)
        print("✅ MetaGPT Demo 执行成功！")
        print("=" * 60)
        print()
        print("生成的内容预览：")
        print("-" * 60)
        # 显示前 500 个字符
        preview = result[:500] if len(result) > 500 else result
        print(preview)
        if len(result) > 500:
            print(f"... (共 {len(result)} 字符)")
        print("-" * 60)
        print()
        print("完整内容已保存到 output/design.md")
        return True

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Demo 执行失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行 demo
    success = asyncio.run(main())
    exit(0 if success else 1)
