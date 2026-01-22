#!/bin/bash
# LEE 框架重组迁移脚本 v3
# 将当前项目重组为标准的 LEE 框架结构
# 使用前请先审核 MIGRATION_PLAN.md
# 执行前请确保已创建备份

set -e  # 遇到错误立即退出

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查备份
check_backup() {
    log_step "检查备份..."
    backup_count=$(find .. -maxdepth 1 -type d -name "LEE-backup-*" 2>/dev/null | wc -l)
    if [ "$backup_count" -eq 0 ]; then
        log_warn "未找到备份目录"
        echo ""
        echo "建议先创建备份："
        echo "  cp -r . ../LEE-backup-\$(date +%Y%m%d)"
        echo ""
        read -p "是否继续？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "找到备份目录"
    fi
}

# 阶段 1：创建目录结构
create_directories() {
    log_step "创建目录结构..."

    mkdir -p flowcore/{orchestrator,engines/metagpt,utils,cli}
    mkdir -p spec-global/core/{workflows,work_items,gates,contracts,teams}
    mkdir -p spec-global/departments/{stg,prd,ui,dev,qa,ops,office}/{workflows,gates,agents,skills,contracts}
    mkdir -p spec-global/cross/{workflows,interfaces,teams}
    mkdir -p config docs changelogs examples tools tests

    log_info "目录结构创建完成"
}

# 阶段 2：迁移 orchestrator
migrate_orchestrator() {
    log_step "迁移 orchestrator..."

    local moved=0

    # 移动核心文件（扁平化）
    if [ -d "orchestrator/core" ]; then
        cp -n orchestrator/core/*.py flowcore/orchestrator/ 2>/dev/null && ((moved++)) || true
    fi

    # 移动顶层文件
    if [ -f "orchestrator/__init__.py" ]; then
        cp -n orchestrator/__init__.py flowcore/orchestrator/ && ((moved++)) || true
    fi

    # 移动 CLI
    if [ -f "orchestrator/__main__.py" ]; then
        cp -n orchestrator/__main__.py flowcore/cli/main.py && ((moved++)) || true
    fi

    if [ -f "orchestrator/cli.py" ]; then
        cp -n orchestrator/cli.py flowcore/cli/commands.py && ((moved++)) || true
    fi

    # 移动文档
    if [ -d "orchestrator/docs" ]; then
        cp -n orchestrator/docs/*.md docs/ 2>/dev/null && ((moved++)) || true
    fi

    if [ -f "orchestrator/README.md" ]; then
        cp -n orchestrator/README.md docs/Orchestrator-Guide.md && ((moved++)) || true
    fi

    if [ -f "orchestrator/INTEGRATION.md" ]; then
        cp -n orchestrator/INTEGRATION.md docs/Integration-Guide.md && ((moved++)) || true
    fi

    # 移动示例
    if [ -d "orchestrator/examples" ]; then
        cp -rn orchestrator/examples/* examples/ 2>/dev/null && ((moved++)) || true
    fi

    log_info "orchestrator 迁移完成，移动了 $moved 个文件"
}

# 阶段 3：迁移 MetaGPT 适配层
migrate_metagpt_adapter() {
    log_step "迁移 MetaGPT 适配层..."

    local moved=0

    if [ -d "MetaGPT/metagpt/lee" ]; then
        cp -n MetaGPT/metagpt/lee/*.py flowcore/engines/metagpt/ && ((moved++)) || true
        log_info "MetaGPT 适配层迁移完成"
    else
        log_warn "未找到 MetaGPT 适配层目录"
    fi

    # 移动文档
    if [ -f "MetaGPT/LEE_ADAPTER_SUMMARY.md" ]; then
        cp -n MetaGPT/LEE_ADAPTER_SUMMARY.md docs/MetaGPT-Integration.md && ((moved++)) || true
    fi

    log_info "移动了 $moved 个文件"
}

# 阶段 4：迁移 ai-spec（按部门重组）
migrate_ai_spec() {
    log_step "迁移 ai-spec（按部门重组）..."

    local moved=0

    # 4.1 迁移战略部门 (stg) agents
    log_info "  迁移战略部门 (stg)..."
    if [ -d "ai-spec/specs/common/agents" ]; then
        for agent in business-opportunity-analyzer supply-analyzer google-keyword-searcher google-trend-analyzer industry-structure-analyzer; do
            find "ai-spec/specs/common/agents" -name "*${agent}*" -type f 2>/dev/null | while read file; do
                if [ -n "$file" ]; then
                    cp -n "$file" "spec-global/departments/stg/agents/" 2>/dev/null && ((moved++)) || true
                fi
            done
        done
    fi

    # 4.2 迁移 UI 设计部门 (ui) agents
    log_info "  迁移 UI 设计部门 (ui)..."
    if [ -d "ai-spec/specs/common/agents" ]; then
        for agent in icon-generator ui-contract-generator ui-contract-validator; do
            find "ai-spec/specs/common/agents" -name "*${agent}*" -type f 2>/dev/null | while read file; do
                if [ -n "$file" ]; then
                    cp -n "$file" "spec-global/departments/ui/agents/" 2>/dev/null && ((moved++)) || true
                fi
            done
        done
    fi

    # 4.3 迁移产品部门 (prd) agents
    log_info "  迁移产品部门 (prd)..."
    if [ -d "ai-spec/specs/common/agents" ]; then
        for agent in prd-writer requirement-reviewer product-goal-analyzer; do
            find "ai-spec/specs/common/agents" -name "*${agent}*" -type f 2>/dev/null | while read file; do
                if [ -n "$file" ]; then
                    cp -n "$file" "spec-global/departments/prd/agents/" 2>/dev/null && ((moved++)) || true
                fi
            done
        done
    fi

    # 4.4 迁移开发部门 (dev) agents
    log_info "  迁移开发部门 (dev)..."
    if [ -d "ai-spec/specs/common/agents" ]; then
        for agent in tech-architect plan-architect; do
            find "ai-spec/specs/common/agents" -name "*${agent}*" -type f 2>/dev/null | while read file; do
                if [ -n "$file" ]; then
                    cp -n "$file" "spec-global/departments/dev/agents/" 2>/dev/null && ((moved++)) || true
                fi
            done
        done
    fi

    # 4.5 迁移测试部门 (qa) agents
    log_info "  迁移测试部门 (qa)..."
    if [ -d "ai-spec/specs/common/agents" ]; then
        for agent in test-case-creator e2e-test-executor; do
            find "ai-spec/specs/common/agents" -name "*${agent}*" -type f 2>/dev/null | while read file; do
                if [ -n "$file" ]; then
                    cp -n "$file" "spec-global/departments/qa/agents/" 2>/dev/null && ((moved++)) || true
                fi
            done
        done
    fi

    # 4.6 迁移 contracts
    log_info "  迁移 contracts..."
    if [ -d "ai-spec/specs/common/contracts" ]; then
        # stg contracts
        find "ai-spec/specs/common/contracts" -name "*business*" -type f 2>/dev/null | while read file; do
            if [ -n "$file" ]; then
                cp -n "$file" "spec-global/departments/stg/contracts/" 2>/dev/null && ((moved++)) || true
            fi
        done

        # prd contracts
        find "ai-spec/specs/common/contracts" -name "*prd*" -o -name "*product*" | while read file; do
            if [ -n "$file" ]; then
                cp -n "$file" "spec-global/departments/prd/contracts/" 2>/dev/null && ((moved++)) || true
            fi
        done

        # ui contracts
        find "ai-spec/specs/common/contracts" -name "*ui*" -type f 2>/dev/null | while read file; do
            if [ -n "$file" ]; then
                cp -n "$file" "spec-global/departments/ui/contracts/" 2>/dev/null && ((moved++)) || true
            fi
        done
    fi

    # 移动核心文档
    if [ -f "ai-spec/AI-CONSTITUTION.md" ]; then
        cp -n ai-spec/AI-CONSTITUTION.md docs/ && ((moved++)) || true
    fi

    if [ -f "ai-spec/core.yaml" ]; then
        cp -n ai-spec/core.yaml config/defaults.yaml && ((moved++)) || true
    fi

    # 移动工具（通用部分）
    if [ -d "ai-spec/tools" ]; then
        cp -rn ai-spec/tools/* tools/ 2>/dev/null && ((moved++)) || true
    fi

    log_info "ai-spec 迁移完成，移动了 $moved 个文件"
}

# 阶段 5：创建基础文件
create_base_files() {
    log_step "创建基础文件..."

    # 创建 flowcore/__init__.py
    if [ ! -f "flowcore/__init__.py" ]; then
        cat > flowcore/__init__.py << 'EOF'
"""
LEE 框架 - 通用 AI 工作流编排系统

核心代码包：flowcore
"""

__version__ = "0.1.0"
EOF
        log_info "创建 flowcore/__init__.py"
    fi

    # 创建 pyproject.toml 模板
    if [ ! -f "pyproject.toml" ]; then
        cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lee-framework"
version = "0.1.0"
description = "通用 AI 工作流编排框架"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.0",
]

[project.optional-dependencies]
metagpt = [
    "metagpt>=0.8.0",
]
dev = [
    "pytest>=7.0",
    "black>=23.0",
    "flake8>=6.0",
]

[project.scripts]
lee = "flowcore.cli.main:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["flowcore*"]

[tool.black]
line-length = 100
target-version = ['py38']

[tool.pytest.ini_options]
testpaths = ["tests"]
EOF
        log_info "创建 pyproject.toml"
    fi

    log_info "基础文件创建完成"
}

# 阶段 6：创建部门 README 文档
create_department_readmes() {
    log_step "创建部门 README 文档..."

    python tools/create_department_readmes.py

    log_info "部门 README 创建完成"
}

# 生成迁移报告
generate_report() {
    log_step "生成迁移报告..."

    cat > MIGRATION_REPORT.md << EOF
# LEE 框架迁移报告

> 生成时间：$(date)

## 迁移统计

- 新增目录：$(find flowcore spec-global config docs examples tools tests 2>/dev/null | wc -l)
- 新增文件：$(find flowcore spec-global config docs examples tools tests -type f 2>/dev/null | wc -l)

## 主要目录

\`\`\`
$(find flowcore spec-global/departments config docs -maxdepth 2 -type d 2>/dev/null | sed 's|^\./||' | sort | head -50)
\`\`\`

## 部门结构

\`\`\`
spec-global/departments/
├── stg/        # 战略部门
├── prd/        # 产品部门
├── ui/         # UI 设计部门
├── dev/        # 开发部门
├── qa/         # 测试部门
├── ops/        # 运维部门
└── office/     # 办公室/行政
\`\`\`

## 下一步操作

### 1. 审核迁移的文件

请检查以下目录中的文件是否正确：

- \`flowcore/\` - 核心代码
- \`spec-global/\` - 全局规范
- \`docs/\` - 框架文档
- \`config/\` - 配置文件

### 2. 更新 Import 路径

运行以下命令更新所有 Python 文件的 import 语句：

\`\`\`bash
python tools/update_imports.py
\`\`\`

### 3. 验证 Python 语法

\`\`\`bash
python -m py_compile flowcore/**/*.py
\`\`\`

### 4. 查看部门 README

每个部门都有独立的 README.md 文档：

\`\`\`
cat spec-global/departments/stg/README.md
cat spec-global/departments/prd/README.md
cat spec-global/departments/ui/README.md
cat spec-global/departments/dev/README.md
cat spec-global/departments/qa/README.md
cat spec-global/departments/ops/README.md
cat spec-global/departments/office/README.md
\`\`\`

### 5. 运行测试（如果有）

\`\`\`bash
pytest tests/
\`\`\`

### 6. 删除原始目录（确认无误后）

⚠️ **警告：删除前请确保所有文件已正确迁移**

\`\`\`bash
# 删除原始目录
rm -rf orchestrator
rm -rf ai-spec

# 保留 MetaGPT 核心库，只删除适配层
rm -rf MetaGPT/metagpt/lee

# 或者，如果 MetaGPT 是外部依赖，可以保留整个目录
\`\`\`

### 7. 提交到版本控制

\`\`\`bash
git add .
git commit -m "重构: 重组为 LEE 框架标准结构 v3"
\`\`\`

## 需要手动创建的文件

迁移脚本已创建基础文件，但以下文件需要手动完善：

- \`flowcore/engines/base.py\` - LEE 接口定义（LEERequest, LEEResult 等）
- \`flowcore/orchestrator/runner.py\` - 工作流运行器
- \`flowcore/orchestrator/dag_executor.py\` - DAG 执行器
- \`config/logging.yaml\` - 日志配置

## 部门 README 文档

已为以下部门创建 README.md：

- stg/ - 战略部门
- prd/ - 产品部门
- ui/ - UI 设计部门
- dev/ - 开发部门
- qa/ - 测试部门
- ops/ - 运维部门
- office/ - 办公室/行政

每个部门的 README 包含：
- 部门职责
- 目录结构
- 工作流列表
- 门禁列表
- Agent 列表
- 技能列表
- 契约列表
- 跨部门协作

## 回滚

如果需要回滚：

\`\`\`bash
# 删除新结构
rm -rf flowcore spec-global config docs changelogs examples tools tests pyproject.toml

# 恢复备份
cp -r ../LEE-backup-YYYYMMDD/* .
\`\`\`
EOF

    log_info "迁移报告生成完成：MIGRATION_REPORT.md"
}

# 显示摘要
show_summary() {
    echo ""
    echo "======================================"
    echo "迁移完成摘要"
    echo "======================================"
    echo ""
    echo "已创建的目录："
    echo "  - flowcore/               # 核心代码"
    echo "  - spec-global/            # 全局规范（按 7 个部门组织）"
    echo "  - config/                 # 配置模板"
    echo "  - docs/                   # 框架文档"
    echo "  - changelogs/             # 变更日志"
    echo "  - examples/               # 使用示例"
    echo "  - tools/                  # 工具脚本"
    echo "  - tests/                  # 框架测试"
    echo ""
    echo "部门结构："
    echo "  - stg/    # 战略部门"
    echo "  - prd/    # 产品部门"
    echo "  - ui/     # UI 设计部门"
    echo "  - dev/    # 开发部门"
    echo "  - qa/     # 测试部门"
    echo "  - ops/    # 运维部门"
    echo "  - office/ # 办公室/行政"
    echo ""
    log_warn "请检查迁移结果，确认无误后："
    echo "  1. 运行: python tools/update_imports.py"
    echo "  2. 运行: python -m py_compile flowcore/**/*.py"
    echo "  3. 查看报告: cat MIGRATION_REPORT.md"
    echo "  4. 查看部门文档: ls spec-global/departments/*/README.md"
    echo ""
    log_warn "确认无误后，可以删除原始目录："
    echo "  rm -rf orchestrator ai-spec MetaGPT/metagpt/lee"
    echo ""
}

# 主流程
main() {
    echo "======================================"
    echo "LEE 框架重组迁移脚本 v3"
    echo "======================================"
    echo ""

    check_backup

    read -p "是否开始迁移？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "已取消迁移"
        exit 0
    fi

    log_info "开始迁移..."
    echo ""

    create_directories
    migrate_orchestrator
    migrate_metagpt_adapter
    migrate_ai_spec
    create_base_files
    create_department_readmes
    generate_report

    show_summary
}

# 执行
main "$@"
