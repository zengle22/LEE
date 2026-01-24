#!/bin/bash
# LEE 环境快速设置脚本

set -e

echo "🚀 LEE 环境快速设置"
echo "===================="

# 1. 复制环境变量模板
if [ ! -f .env ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env
    echo "✅ .env 文件已创建"
else
    echo "✅ .env 文件已存在"
fi

# 2. 安装依赖
echo ""
echo "📦 安装 Python 依赖..."
python scripts/install_requirements.py

# 3. 设置环境
echo ""
echo "⚙️  设置环境..."
python scripts/setup_env.py

# 4. 运行测试
echo ""
echo "🧪 运行测试..."
python scripts/test_all.py

echo ""
echo "✅ 设置完成！"
