#!/usr/bin/env python3
"""
LEE 环境安装脚本
安装所有必需的依赖
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """运行命令并显示输出"""
    print(f"\n▶ {description}")
    print(f"  命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print(f"  输出: {result.stdout.strip()}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"  ❌ 错误: {e.stderr}")
        return False


def install_python_deps():
    """安装 Python 依赖"""
    print("\n" + "=" * 60)
    print("📦 安装 Python 依赖")
    print("=" * 60)

    requirements = [
        # 核心依赖
        ("pyyaml", "YAML 配置文件解析"),
        ("aiohttp", "异步 HTTP 客户端"),
        ("python-dotenv", "环境变量管理"),

        # 可选依赖
        ("openai", "OpenAI API 客户端"),
    ]

    for package, description in requirements:
        run_command(
            [sys.executable, "-m", "pip", "install", package],
            f"安装 {package} - {description}"
        )

    print("\n✅ Python 依赖安装完成")


def install_mcp_server():
    """安装 MCP Server（Node.js）"""
    print("\n" + "=" * 60)
    print("📦 安装 MCP Server")
    print("=" * 60)

    mcp_dir = Path(__file__).parent.parent / "mcp-server"

    if not mcp_dir.exists():
        print(f"❌ MCP Server 目录不存在: {mcp_dir}")
        return False

    # 检查 Node.js
    if not run_command(["node", "--version"], "检查 Node.js 版本"):
        print("❌ Node.js 未安装，跳过 MCP Server 安装")
        print("   提示: 从 https://nodejs.org/ 下载安装")
        return False

    # 检查 npm
    if not run_command(["npm", "--version"], "检查 npm 版本"):
        print("❌ npm 未安装")
        return False

    # 安装依赖
    success = run_command(
        ["npm", "install"],
        "安装 MCP Server 依赖"
    )

    if success:
        print("\n✅ MCP Server 安装完成")
        print("\n💡 启动 MCP Server:")
        print(f"   cd {mcp_dir}")
        print("   npm start")
    else:
        print("\n❌ MCP Server 安装失败")
        return False

    return True


def create_gitignore():
    """创建 .gitignore 文件"""
    print("\n" + "=" * 60)
    print("📝 创建 .gitignore")
    print("=" * 60)

    project_root = Path(__file__).parent.parent
    gitignore_path = project_root / ".gitignore"

    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
venv/
ENV/
env/

# 环境变量
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 工作流
.workflow/
*.log

# Node.js
node_modules/
npm-debug.log
yarn-error.log

# OS
.DS_Store
Thumbs.db

# 测试
.pytest_cache/
.coverage
htmlcov/
.tox/

# 临时文件
*.tmp
*.bak
"""

    try:
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)

        print(f"✅ .gitignore 创建成功: {gitignore_path}")
        return True

    except Exception as e:
        print(f"❌ 创建 .gitignore 失败: {e}")
        return False


def verify_installation():
    """验证安装"""
    print("\n" + "=" * 60)
    print("🔍 验证安装")
    print("=" * 60)

    # 检查 Python 模块
    modules_to_check = [
        "yaml",
        "aiohttp",
        "dotenv",
        "openai"
    ]

    print("\n检查 Python 模块:")
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} - 未安装")

    # 检查 MCP Server
    print("\n检查 MCP Server:")
    mcp_dir = Path(__file__).parent.parent / "mcp-server" / "node_modules"
    if mcp_dir.exists():
        print(f"  ✅ MCP Server 已安装")
    else:
        print(f"  ⚠️  MCP Server 未安装")

    print("\n✅ 安装验证完成")


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("  LEE 环境安装")
    print("🚀" * 30)

    # 安装 Python 依赖
    install_python_deps()

    # 安装 MCP Server
    install_mcp_server()

    # 创建 .gitignore
    create_gitignore()

    # 验证安装
    verify_installation()

    print("\n" + "=" * 60)
    print("✅ 安装完成！")
    print("=" * 60)
    print("\n💡 下一步:")
    print("  1. 配置环境变量: cp .env.example .env")
    print("  2. 编辑 .env 文件，填入 API keys")
    print("  3. 运行环境设置: python scripts/setup_env.py")
    print("  4. 测试 LLM: python scripts/test_llm.py")
    print("  5. 启动 MCP Server: cd mcp-server && npm start")
    print("  6. 测试 MCP: python scripts/test_mcp.py")


if __name__ == "__main__":
    main()
