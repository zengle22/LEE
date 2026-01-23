#!/bin/bash
# STG Opportunity Discovery Demo Runner
# 商业机会发现演示运行器

echo "🚀 STG Opportunity Discovery Demo"
echo "================================"
echo ""

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    exit 1
fi

# 运行测试
echo "📋 Running workflow test..."
echo ""

python test_workflow.py

echo ""
echo "✅ Demo completed!"
echo ""
echo "📁 Generated files will be in:"
echo "  - spec-global/departments/stg/contracts/"
echo "  - spec-global/departments/stg/examples/"
