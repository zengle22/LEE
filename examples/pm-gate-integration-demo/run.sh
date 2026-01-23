#!/bin/bash
# LEE PM Agent + Gate Assistant Integration Demo Runner

set -e

echo "🚀 LEE PM Agent + Gate Assistant Integration Demo"
echo "================================================"
echo ""

# Set project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/src"

echo "📁 Project root: ${PROJECT_ROOT}"
echo ""

# Check if flowcore is available
echo "🔍 Checking flowcore installation..."
python -c "import flowcore.api; print('✓ flowcore.api available')" || {
    echo "❌ flowcore.api not found"
    echo "Please ensure flowcore is installed or PYTHONPATH is set correctly"
    exit 1
}

echo ""
echo "▶ Running integration demo..."
echo ""

# Run the demo
python "${PROJECT_ROOT}/examples/pm-gate-integration-demo/test_pm_gate_integration.py"

echo ""
echo "✅ Demo completed!"
