#!/usr/bin/env python3
"""
PM Agent 快速入门 - 最小化示例

这是一个最简单的 PM Agent 使用示例，适合快速上手。
"""

import sys
from pathlib import Path

# 添加项目路径
# 从 examples/pm-agent-stg-workflow 到项目根目录需要向上两级
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent.parent  # 向上两级到项目根目录
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 加载环境
import os
from dotenv import load_dotenv

# 加载 .env 文件
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)

from flowcore.api import (
    api_get_state,
    api_list_ready_steps,
    api_run_step,
    api_next_step,
)


def main():
    """主函数 - 最简单的 PM Agent 示例"""

    print("\n" + "=" * 60)
    print("  PM Agent 快速入门")
    print("=" * 60)

    # STG 部门目录
    project_dir = str(PROJECT_ROOT / "spec-global" / "departments" / "stg")

    # 检查 workflow 文件
    workflow_file = Path(project_dir) / "workflows" / "opportunity_discovery" / "v1" / "workflow.yaml"
    if not workflow_file.exists():
        print(f"❌ Workflow 文件不存在: {workflow_file}")
        print(f"\n💡 请确保 STG workflow 已创建")
        return

    # 初始化 workflow（如果还没有）
    import subprocess
    state_dir = Path(project_dir) / ".workflow"
    if not state_dir.exists():
        print(f"\n⚙️  初始化 workflow...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "flowcore.orchestrator.cli", "init",
                 project_dir, "-w", str(workflow_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"✅ Workflow 初始化成功")
            else:
                print(f"⚠️  初始化警告: {result.stderr}")
        except Exception as e:
            print(f"⚠️  初始化跳过: {e}")

    # ========================================
    # 步骤 1: 查看工作流状态
    # ========================================
    print("\n📊 步骤 1: 查看工作流状态")
    print("-" * 60)

    state = api_get_state(project_dir)

    if "error" in state:
        print(f"❌ 错误: {state['error']}")
        print("\n💡 提示: 请先运行 'python -m flowcore.orchestrator.cli init'")
        return

    print(f"✅ 工作流: {state.get('workflow_name', 'Unknown')}")
    print(f"   进度: {state['completed_steps']}/{state['total_steps']}")
    print(f"   就绪: {len(state.get('ready_steps', []))} 个步骤")

    # ========================================
    # 步骤 2: 列出就绪步骤
    # ========================================
    print("\n📋 步骤 2: 列出就绪步骤")
    print("-" * 60)

    ready_steps = api_list_ready_steps(project_dir)

    if not ready_steps:
        print("⚠️  当前没有就绪的步骤")
        print("\n可能原因:")
        print("  1. 工作流已完成")
        print("  2. 需要等待人工审批")
        print("  3. 有步骤失败")
        return

    print(f"✅ 找到 {len(ready_steps)} 个就绪步骤:")
    for i, step in enumerate(ready_steps, 1):
        print(f"   {i}. {step['id']}: {step.get('description', 'No description')}")

    # ========================================
    # 步骤 3: 执行第一个就绪步骤
    # ========================================
    print("\n⚙️  步骤 3: 执行步骤")
    print("-" * 60)

    step_to_execute = ready_steps[0]
    step_id = step_to_execute['id']

    print(f"🎯 执行步骤: {step_id}")
    print(f"   描述: {step_to_execute.get('description', 'N/A')}")
    print(f"\n⏳ 正在执行...")

    result = api_run_step(project_dir, step_id)

    # ========================================
    # 步骤 4: 查看执行结果
    # ========================================
    print("\n📈 步骤 4: 执行结果")
    print("-" * 60)

    if result["status"] == "completed":
        print(f"✅ 步骤完成!")
        print(f"   耗时: {result.get('duration_seconds', 0):.2f} 秒")
        print(f"   引擎: {result.get('engine_type', 'unknown')}")

        if "outputs" in result and result["outputs"]:
            print(f"\n📁 输出文件 ({len(result['outputs'])} 个):")
            for output in result["outputs"]:
                print(f"      - {output}")

    elif result["status"] == "failed":
        print(f"❌ 步骤失败")
        print(f"   错误: {result.get('error', 'Unknown')}")

    else:
        print(f"⚠️  步骤状态: {result['status']}")

    # ========================================
    # 步骤 5: 查看最新状态
    # ========================================
    print("\n🔄 步骤 5: 最新状态")
    print("-" * 60)

    state = api_get_state(project_dir)
    progress_pct = (
        state['completed_steps'] / state['total_steps'] * 100
        if state['total_steps'] > 0 else 0
    )

    print(f"当前进度: {state['completed_steps']}/{state['total_steps']} ({progress_pct:.1f}%)")
    print(f"就绪步骤: {len(state.get('ready_steps', []))} 个")
    print(f"失败步骤: {state.get('failed_steps', 0)} 个")

    # ========================================
    # 进阶: 自动执行所有步骤
    # ========================================
    print("\n" + "=" * 60)
    print("💡 进阶提示")
    print("=" * 60)
    print("\n如果想自动执行所有步骤，可以使用:")
    print("\n  from flowcore.api import api_next_step")
    print("  result = api_next_step(project_dir)")
    print("\n或运行完整示例:")
    print("  python run_stg_with_pm_agent.py")

    print("\n" + "=" * 60)
    print("✅ 快速入门完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
