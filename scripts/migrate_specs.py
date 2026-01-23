#!/usr/bin/env python3
"""
Spec Migration Script
将旧 ai-spec/specs 结构迁移到新的 spec-global 结构
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List

# 源目录和目标目录
SOURCE_ROOT = Path("E:/ai/LEE/ai-spec/specs")
TARGET_ROOT = Path("E:/ai/LEE/spec-global")

# 迁移映射表
MIGRATION_MAP = [
    # ============================================
    # Phase 1: org 直接映射
    # ============================================
    # development → dev
    ("org/development/agents", "departments/dev/agents"),
    ("org/development/contracts", "departments/dev/contracts"),
    ("org/development/gates", "departments/dev/gates"),
    ("org/development/workflows", "departments/dev/workflows"),
    ("org/development/standards", "departments/dev/contracts"),  # standards → contracts

    # product → prd
    ("org/product/agents", "departments/prd/agents"),
    ("org/product/workflows", "departments/prd/workflows"),

    # testing → qa
    ("org/testing/agents", "departments/qa/agents"),
    ("org/testing/contracts", "departments/qa/contracts"),
    ("org/testing/gates", "departments/qa/gates"),
    ("org/testing/workflows", "departments/qa/workflows"),

    # integration → qa (integration 测试)
    ("org/integration", "departments/qa/integration"),

    # ============================================
    # Phase 2: common → 各部门分类
    # ============================================

    # --- 产品相关 → prd ---
    ("common/agents/prd-writer", "departments/prd/agents/prd-writer"),
    ("common/agents/product-goal-analyzer", "departments/prd/agents/product-goal-analyzer"),
    ("common/agents/requirement-reviewer", "departments/prd/agents/requirement-reviewer"),
    ("common/agents/requirement-alignment", "departments/prd/agents/requirement-alignment"),

    # --- 设计/UI 相关 → ui ---
    ("common/agents/ui-designer", "departments/ui/agents/ui-designer"),
    ("common/agents/ui-contract-generator", "departments/ui/agents/ui-contract-generator"),
    ("common/agents/ui-contract-validator", "departments/ui/agents/ui-contract-validator"),
    ("common/agents/ui-design-executor", "departments/ui/agents/ui-design-executor"),
    ("common/agents/ui-gate-runner", "departments/ui/gates/ui-gate-runner"),
    ("common/agents/ui-test-generator", "departments/ui/agents/ui-test-generator"),
    ("common/agents/ux-review-agent", "departments/ui/agents/ux-review-agent"),
    ("common/agents/icon-generator", "departments/ui/agents/icon-generator"),
    ("common/agents/prototype-designer", "departments/ui/agents/prototype-designer"),

    ("common/skills/figma-component-builder", "departments/ui/skills/figma-component-builder"),
    ("common/skills/figma-design-system", "departments/ui/skills/figma-design-system"),
    ("common/skills/figma-interaction-design", "departments/ui/skills/figma-interaction-design"),
    ("common/skills/figma-parser", "departments/ui/skills/figma-parser"),
    ("common/skills/design-token-generator", "departments/ui/skills/design-token-generator"),
    ("common/skills/auto-layout-master", "departments/ui/skills/auto-layout-master"),
    ("common/skills/variant-system", "departments/ui/skills/variant-system"),
    ("common/skills/web-prototype-renderer", "departments/ui/skills/web-prototype-renderer"),
    ("common/skills/ui-prompt-enhancer", "departments/ui/skills/ui-prompt-enhancer"),
    ("common/skills/ui-gate-check", "departments/ui/skills/ui-gate-check"),

    ("common/contracts/icon-design-token", "departments/ui/contracts/icon-design-token"),
    ("common/contracts/ux-review-contract", "departments/ui/contracts/ux-review-contract"),
    ("common/gates/ui-gate", "departments/ui/gates/ui-gate"),
    ("common/workflows/ui-design-pipeline", "departments/ui/workflows/ui-design-pipeline"),

    # --- 开发相关 → dev ---
    ("common/agents/tech-architect", "departments/dev/agents/tech-architect"),
    ("common/agents/plan-architect", "departments/dev/agents/plan-architect"),

    # --- 测试相关 → qa ---
    ("common/agents/e2e-test-executor", "departments/qa/agents/e2e-test-executor"),
    ("common/agents/test-case-creator", "departments/qa/agents/test-case-creator"),
    ("common/skills/e2e-runner", "departments/qa/skills/e2e-runner"),

    # --- 策略/商业洞察 → stg ---
    ("common/agents/business-opportunity-analyzer", "departments/stg/agents/business-opportunity-analyzer"),
    ("common/agents/business-opportunity-builder", "departments/stg/agents/business-opportunity-builder"),
    ("common/agents/google-keyword-searcher", "departments/stg/agents/google-keyword-searcher"),
    ("common/agents/google-trend-analyzer", "departments/stg/agents/google-trend-analyzer"),
    ("common/agents/industry-structure-analyzer", "departments/stg/agents/industry-structure-analyzer"),
    ("common/agents/supply-analyzer", "departments/stg/agents/supply-analyzer"),
    ("common/agents/user-signal-analyzer", "departments/stg/agents/user-signal-analyzer"),
    ("common/skills/product-goal-analysis", "departments/stg/skills/product-goal-analysis"),
    ("common/skills/value-analysis-guide", "departments/stg/skills/value-analysis-guide"),
    ("common/skills/requirement-discovery", "departments/prd/skills/requirement-discovery"),

    # --- 审批/门控/不确定归属 → office ---
    ("common/agents/approval-reviewer", "departments/office/agents/approval-reviewer"),
    ("common/agents/phase-acceptance-gate", "departments/office/gates/phase-acceptance"),
    ("common/skills/dev-gate-check", "departments/office/skills/dev-gate-check"),
    ("common/skills/release-gate-check", "departments/office/skills/release-gate-check"),

    # ============================================
    # Phase 3: 核心基础设施 → core/
    # ============================================
    ("common/agents/agent-spec-maintainer", "core/agents/agent-spec-maintainer"),
    ("common/agents/contracts-spec-maintainer", "core/agents/contracts-spec-maintainer"),
    ("common/agents/gates-spec-maintainer", "core/agents/gates-spec-maintainer"),
    ("common/agents/skills-spec-maintainer", "core/agents/skills-spec-maintainer"),
    ("common/agents/workflow-spec-maintainer", "core/agents/workflow-spec-maintainer"),
    ("common/agents/spec-review", "core/agents/spec-review"),

    ("common/contracts/plan-contract", "core/contracts/plan-contract"),
    ("common/contracts/execution-trace", "core/contracts/execution-trace"),

    ("common/protocols/knowledge-access", "core/protocols/knowledge-access"),
    ("common/protocols/tool-wrapper", "core/protocols/tool-wrapper"),

    # ============================================
    # Phase 4: 跨部门协作 → cross/
    # ============================================
    ("common/agents/execution-observer", "cross/agents/execution-observer"),
    ("common/agents/dev-freeze-orchestrator", "cross/agents/dev-freeze-orchestrator"),
    ("common/agents/analysis-freezer", "cross/agents/analysis-freezer"),
    ("common/agents/fact-collector", "cross/agents/fact-collector"),

    ("common/skills/state-validator", "cross/skills/state-validator"),
    ("common/skills/generate-execution-report", "cross/skills/generate-execution-report"),
    ("common/skills/contract-template", "cross/skills/contract-template"),

    ("common/workflows/product-pipeline", "cross/workflows/product-pipeline"),
]


def migrate_item(source: Path, target: Path):
    """迁移单个项目（文件或目录）"""
    if not source.exists():
        print(f"  ⚠️  源不存在，跳过: {source}")
        return False

    # 创建目标目录
    target.parent.mkdir(parents=True, exist_ok=True)

    # 如果目标已存在，跳过
    if target.exists():
        print(f"  ℹ️  目标已存在，跳过: {target}")
        return False

    # 复制
    if source.is_dir():
        shutil.copytree(source, target)
        print(f"  ✓ 复制目录: {source} → {target}")
    else:
        shutil.copy2(source, target)
        print(f"  ✓ 复制文件: {source} → {target}")

    return True


def main():
    """执行迁移"""
    print("="*60)
    print("Spec 迁移开始")
    print("="*60)

    success_count = 0
    skip_count = 0
    error_count = 0

    for source_rel, target_rel in MIGRATION_MAP:
        source_path = SOURCE_ROOT / source_rel
        target_path = TARGET_ROOT / target_rel

        print(f"\n迁移: {source_rel} → {target_rel}")

        try:
            if migrate_item(source_path, target_path):
                success_count += 1
            else:
                skip_count += 1
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            error_count += 1

    print("\n" + "="*60)
    print("迁移完成")
    print(f"  成功: {success_count}")
    print(f"  跳过: {skip_count}")
    print(f"  错误: {error_count}")
    print("="*60)


if __name__ == "__main__":
    main()
