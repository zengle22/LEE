#!/usr/bin/env python3
"""
环境设置脚本
加载 .env 文件并配置环境
"""

import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def load_env():
    """加载 .env 文件"""
    env_file = PROJECT_ROOT / ".env"

    if not env_file.exists():
        print(f"❌ .env 文件不存在: {env_file}")
        print(f"请先复制 .env.example 为 .env 并配置")
        return False

    # 读取 .env 文件
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue

            # 解析 KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

    print(f"✅ 已加载环境配置: {env_file}")
    return True


def setup_pythonpath():
    """设置 PYTHONPATH"""
    src_dir = PROJECT_ROOT / "src"
    project_root = PROJECT_ROOT

    paths = [str(src_dir), str(project_root)]

    for path in paths:
        if path not in sys.path:
            sys.path.insert(0, path)

    os.environ['PYTHONPATH'] = os.pathsep.join(paths)
    print(f"✅ PYTHONPATH 已设置: {os.environ['PYTHONPATH']}")


def verify_env():
    """验证环境配置"""
    print("\n🔍 验证环境配置...")

    required_vars = [
        'OPENAI_BASE_URL',
        'OPENAI_API_KEY',
        'OPENAI_MODEL',
        'ZHIPU_API_KEY',
    ]

    missing = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # 隐藏 API key 的敏感部分
            if 'KEY' in var and len(value) > 8:
                display_value = value[:4] + '...' + value[-4:]
            else:
                display_value = value
            print(f"  ✓ {var} = {display_value}")
        else:
            print(f"  ✗ {var} 未设置")
            missing.append(var)

    if missing:
        print(f"\n❌ 缺少必需的环境变量: {', '.join(missing)}")
        return False

    print("\n✅ 环境配置验证通过")
    return True


def main():
    """主函数"""
    print("🚀 LEE 环境设置")
    print("=" * 60)

    # 加载 .env
    if not load_env():
        sys.exit(1)

    # 设置 PYTHONPATH
    setup_pythonpath()

    # 验证环境
    if not verify_env():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ 环境设置完成！")
    print("\n💡 下一步:")
    print("  1. 运行测试: python scripts/test_env.py")
    print("  2. 测试 LLM: python scripts/test_llm.py")
    print("  3. 测试 MetaGPT: python scripts/test_metagpt.py")


if __name__ == "__main__":
    main()
