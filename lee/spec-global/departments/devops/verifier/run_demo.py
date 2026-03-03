#!/usr/bin/env python3
"""
Demo 测试脚本 - Verifier System

运行 Verifier System 的端到端测试，演示 Phase 1 验证流程。
"""

import os
import sys
import json
import shutil
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from verifier.engine import VerifierEngine, VerificationStatus


def setup_demo_environment():
    """设置 demo 测试环境"""
    base_dir = project_root / "demo"
    phase1_dir = base_dir / "01-architecture"

    # 创建测试目录结构: test-phase1/devops/phase1/
    test_phase1_dir = base_dir / "test-phase1"
    test_devops_dir = test_phase1_dir / "devops" / "phase1"
    test_devops_dir.mkdir(parents=True, exist_ok=True)

    # 复制 demo 文件到测试目录 (使用正确的结构)
    src_files = {
        "infra-architecture.yaml": "infra-architecture.yaml",
        "env-matrix.yaml": "env-matrix.yaml",
    }

    for src, dst in src_files.items():
        src_path = phase1_dir / src
        dst_path = test_devops_dir / dst
        if src_path.exists() and not dst_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"✓ Copied {src} to test-phase1/devops/phase1/")

    # 创建一个简单的 release-strategy.md
    release_strategy = test_devops_dir / "release-strategy.md"
    if not release_strategy.exists():
        release_strategy.write_text("""# 发布策略

## 发布流程
1. dev 环境自动部署
2. test 环境需要审批
3. 生产环境需要多级审批

## 回滚方案
- 使用 docker-compose down 快速回滚
- 数据库备份恢复
""", encoding='utf-8')
        print(f"✓ Created release-strategy.md")

    return test_phase1_dir


def run_phase1_verification_test():
    """运行 Phase 1 验证测试"""
    print("=" * 60)
    print("Verifier System Demo - Phase 1 验证测试")
    print("=" * 60)
    print()

    # 设置测试环境
    print("📁 设置测试环境...")
    test_dir = setup_demo_environment()
    print()

    # 创建验证引擎
    print("🔧 初始化验证引擎...")
    engine = VerifierEngine(config_path=str(project_root / "verifier" / "config.yaml"))
    print(f"   配置文件: {engine.config_path}")
    print(f"   契约目录: {engine.contracts_dir}")
    print(f"   规则目录: {engine.rules_dir}")
    print()

    # 定义测试产物
    artifacts = {
        "architecture_doc": "infra-architecture.yaml",
        "env_matrix": "env-matrix.yaml",
        "release_strategy": "release-strategy.md",
    }

    print("🎯 开始验证 Phase 1 架构设计...")
    print(f"   契约 ID: devops.phase1.architecture.v1")
    print(f"   产物: {list(artifacts.values())}")
    print()

    try:
        # 执行验证
        result = engine.verify(
            contract_id="devops.phase1.architecture.v1",
            artifacts=artifacts,
            base_dir=str(test_dir)
        )

        # 显示结果
        print()
        print("=" * 60)
        print("验证结果")
        print("=" * 60)
        print()
        print(f"总体状态: {result.overall_status.value.upper()}")
        print(f"总检查数: {result.total_checks}")
        print(f"  - 通过: {result.passed_checks}")
        print(f"  - 失败: {result.failed_checks}")
        print(f"  - 警告: {result.warning_checks}")
        print()
        print("摘要:", result.summary)
        print()

        # 显示详细结果
        print("详细检查结果:")
        print("-" * 60)
        for check in result.check_results:
            status_icon = "✅" if check.status == VerificationStatus.PASS else "❌" if check.status == VerificationStatus.FAIL else "⚠️"
            print(f"\n{status_icon} {check.check_name}")
            print(f"   类型: {check.check_type.value}")
            print(f"   状态: {check.status.value}")
            print(f"   严重程度: {check.severity.value}")
            print(f"   详情: {check.detail}")
            if check.score is not None:
                print(f"   评分: {check.score:.2f}")
            if check.suggestions:
                print(f"   建议:")
                for suggestion in check.suggestions:
                    print(f"     - {suggestion}")
            print(f"   耗时: {check.execution_time:.3f}s")

        print()
        print("=" * 60)

        # 检查结果文件
        result_file = test_dir / "verification-result.yaml"
        report_file = test_dir / "verification-report.md"

        if result_file.exists():
            print(f"✓ 结果文件已生成: {result_file}")
        if report_file.exists():
            print(f"✓ 报告文件已生成: {report_file}")

        print()
        print("Demo 完成!")

        # 返回退出码
        if result.overall_status == VerificationStatus.PASS:
            return 0
        elif result.overall_status == VerificationStatus.WARNING:
            return 2
        else:
            return 1

    except Exception as e:
        print()
        print("❌ 验证过程中出错!")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """主入口"""
    exit_code = run_phase1_verification_test()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
