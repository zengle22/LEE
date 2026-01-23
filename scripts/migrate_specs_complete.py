#!/usr/bin/env python3
"""
完整的 Spec 迁移脚本
将所有 spec 文件从 ai-spec/specs 迁移到 spec-global
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List

# 源目录和目标目录
SOURCE_ROOT = Path("E:/ai/LEE/ai-spec/specs")
TARGET_ROOT = Path("E:/ai/LEE/spec-global")

def migrate_directory(source_dir: Path, target_dir: Path, base_msg: str = ""):
    """
    递归迁移目录中的所有文件

    Args:
        source_dir: 源目录
        target_dir: 目标目录
        base_msg: 基础消息
    """
    if not source_dir.exists():
        print(f"  ⚠️  源不存在: {source_dir}")
        return 0

    count = 0
    # 遍历源目录中的所有文件
    for item in source_dir.rglob("*"):
        if item.is_file():
            # 计算相对路径
            rel_path = item.relative_to(source_dir)
            target_file = target_dir / rel_path

            # 创建目标目录
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # 如果目标已存在且内容相同，跳过
            if target_file.exists():
                if target_file.stat().st_size == item.stat().st_size:
                    continue
                # 存在但大小不同，覆盖
                target_file.unlink()

            # 复制文件
            shutil.copy2(item, target_file)
            count += 1
            if count % 10 == 0:
                print(f"    已迁移 {count} 个文件...")

    print(f"  ✓ {base_msg}: 迁移了 {count} 个文件")
    return count


def main():
    """执行完整迁移"""
    print("="*60)
    print("完整 Spec 迁移开始")
    print("="*60)

    total_count = 0

    # ============================================
    # Phase 1: org 部门直接迁移
    # ============================================
    print("\n【Phase 1】迁移 org 部门...")

    # development → dev
    total_count += migrate_directory(
        SOURCE_ROOT / "org/development",
        TARGET_ROOT / "departments/dev",
        "org/development → departments/dev"
    )

    # product → prd
    total_count += migrate_directory(
        SOURCE_ROOT / "org/product",
        TARGET_ROOT / "departments/prd",
        "org/product → departments/prd"
    )

    # testing → qa
    total_count += migrate_directory(
        SOURCE_ROOT / "org/testing",
        TARGET_ROOT / "departments/qa",
        "org/testing → departments/qa"
    )

    # integration → qa/integration
    total_count += migrate_directory(
        SOURCE_ROOT / "org/integration",
        TARGET_ROOT / "departments/qa/integration",
        "org/integration → departments/qa/integration"
    )

    # ============================================
    # Phase 2: common 按类型迁移到各部门
    # ============================================
    print("\n【Phase 2】迁移 common 到各部门...")

    # 迁移映射：(源路径前缀, 目标路径前缀, 描述)
    migrations = [
        # --- 产品相关 → prd ---
        ("common/agents/prd-writer", "departments/prd/agents/prd-writer"),
        ("common/agents/product-goal-analyzer", "departments/prd/agents/product-goal-analyzer"),
        ("common/agents/requirement-reviewer", "departments/prd/agents/requirement-reviewer"),
        ("common/skills/requirement-discovery", "departments/prd/skills/requirement-discovery"),

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
        ("common/skills/figma-import-guide", "departments/ui/skills/figma-import-guide"),
        ("common/skills/design-token-generator", "departments/ui/skills/design-token-generator"),
        ("common/skills/auto-layout-master", "departments/ui/skills/auto-layout-master"),
        ("common/skills/variant-system", "departments/ui/skills/variant-system"),
        ("common/skills/web-prototype-renderer", "departments/ui/skills/web-prototype-renderer"),
        ("common/skills/ui-prompt-enhancer", "departments/ui/skills/ui-prompt-enhancer"),
        ("common/skills/ui-gate-check", "departments/ui/skills/ui-gate-check"),
        ("common/skills/icon-svg-generator", "departments/ui/skills/icon-svg-generator"),
        ("common/skills/ui-ux-pro-max-integration", "departments/ui/skills/ui-ux-pro-max-integration"),

        ("common/contracts/icon-design-token", "departments/ui/contracts/icon-design-token"),
        ("common/contracts/ux-review-contract", "departments/ui/contracts/ux-review-contract"),
        ("common/gates/ui-gate", "departments/ui/gates/ui-gate"),
        ("common/workflows/ui-design-pipeline", "departments/ui/workflows/ui-design-pipeline"),

        # --- 开发相关 → dev ---
        ("common/agents/tech-architect", "departments/dev/agents/tech-architect"),
        ("common/agents/plan-architect", "departments/dev/agents/plan-architect"),
        ("common/skills/planning-methodology", "departments/dev/skills/planning-methodology"),

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
        ("common/skills/agent-spec-creator", "core/skills/agent-spec-creator"),

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

    for src_prefix, dst_prefix in migrations:
        src_path = SOURCE_ROOT / src_prefix
        dst_path = TARGET_ROOT / dst_prefix
        desc = f"{src_prefix} → {dst_prefix}"

        total_count += migrate_directory(src_path, dst_path, desc)

    print("\n" + "="*60)
    print(f"✓ 迁移完成！共迁移 {total_count} 个文件")
    print("="*60)


if __name__ == "__main__":
    main()
