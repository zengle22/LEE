#!/usr/bin/env python3
"""
PM Agent 运行 STG 商业机会发现工作流 - 完整示例

本示例展示如何使用 PM Agent API 管理和执行 STG 部门的商业机会发现工作流。

工作流层次结构：
┌─────────────────────────────────────────────────────────┐
│                  PM Agent (你)                          │
│  职责: 查看状态 → 做决策 → 执行步骤 → 处理结果        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   Orchestrator      │
            │  (自动执行步骤)      │
            └─────────────────────┘
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
# 从 examples/pm-agent-stg-workflow 向上两级到项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
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
    api_run_step_async,
    api_next_step,
    api_gate_list_pending,
    api_gate_show,
    api_gate_decide,
)


class STGWorkflowPM:
    """
    STG 商业机会发现工作流的 PM Agent

    职责：
    1. 查看工作流状态
    2. 做出决策：执行哪个步骤
    3. 处理执行结果
    4. 处理人工审批门控
    """

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.decision_log = []  # 记录决策历史

    def log_decision(self, step_id: str, action: str, reason: str):
        """记录决策"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step_id": step_id,
            "action": action,
            "reason": reason
        }
        self.decision_log.append(log_entry)
        print(f"\n📝 [决策记录] {action}: {step_id}")
        print(f"   理由: {reason}")

    def print_section(self, title: str):
        """打印章节标题"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_subsection(self, title: str):
        """打印子标题"""
        print(f"\n▶ {title}")
        print("-" * 70)

    def analyze_state(self, state: dict) -> dict:
        """
        分析工作流状态，生成决策建议

        Returns:
            决策建议字典
        """
        analysis = {
            "workflow_name": state.get("workflow_name", "Unknown"),
            "total_steps": state.get("total_steps", 0),
            "completed_steps": state.get("completed_steps", 0),
            "failed_steps": state.get("failed_steps", 0),
            "ready_steps": state.get("ready_steps", []),
            "progress_pct": 0,
            "recommendation": None,
            "reason": None
        }

        # 计算进度
        if analysis["total_steps"] > 0:
            analysis["progress_pct"] = (
                analysis["completed_steps"] / analysis["total_steps"] * 100
            )

        # 生成建议
        if analysis["failed_steps"] > 0:
            analysis["recommendation"] = "handle_failure"
            analysis["reason"] = f"有 {analysis['failed_steps']} 个步骤失败，需要处理"
        elif not analysis["ready_steps"]:
            analysis["recommendation"] = "check_gates"
            analysis["reason"] = "没有就绪步骤，可能需要人工审批"
        elif analysis["ready_steps"]:
            analysis["recommendation"] = "execute_next"
            analysis["reason"] = f"有 {len(analysis['ready_steps'])} 个就绪步骤可执行"

        return analysis

    async def run_workflow_interactive(self):
        """
        交互式运行工作流

        PM Agent 会：
        1. 查看状态
        2. 分析情况
        3. 展示决策选项
        4. 等待确认（或自动执行）
        5. 执行步骤
        6. 处理结果
        """
        self.print_section("🚀 PM Agent: STG 商业机会发现工作流")

        print(f"\n📁 项目目录: {self.project_dir}")
        print(f"🤖 PM Agent 角色: 查看 → 决策 → 执行")
        print(f"⚠️  注意: 本示例使用自动模式，PM Agent 会自动做决策")

        # 主循环
        iteration = 0
        max_iterations = 20  # 防止无限循环

        while iteration < max_iterations:
            iteration += 1

            self.print_subsection(f"第 {iteration} 轮决策")

            # 1. 获取当前状态
            state = api_get_state(self.project_dir)

            if "error" in state:
                print(f"❌ 错误: {state['error']}")
                break

            # 2. 分析状态
            analysis = self.analyze_state(state)

            print(f"\n📊 工作流状态:")
            print(f"  名称: {analysis['workflow_name']}")
            print(f"  进度: {analysis['completed_steps']}/{analysis['total_steps']} "
                  f"({analysis['progress_pct']:.1f}%)")
            print(f"  失败: {analysis['failed_steps']}")
            print(f"  就绪: {len(analysis['ready_steps'])} 个步骤")

            # 3. 检查是否完成
            if analysis["completed_steps"] == analysis["total_steps"]:
                self.print_subsection("✅ 工作流已完成！")
                print(f"\n🎉 所有步骤执行完成")
                print(f"   总步骤: {analysis['total_steps']}")
                print(f"   完成率: 100%")
                break

            # 4. 处理人工审批门控
            pending_gates = api_gate_list_pending(self.project_dir)
            if pending_gates:
                self.print_subsection("🚦 遇到人工审批门控")

                for gate in pending_gates:
                    print(f"\n⚠️  门控: {gate['id']}")
                    print(f"   描述: {gate.get('description', 'N/A')}")

                    # 展示门控详情
                    gate_detail = api_gate_show(self.project_dir, gate['id'])

                    if "checklist" in gate_detail:
                        print(f"\n   审批清单:")
                        for item in gate_detail["checklist"]:
                            status = "✓" if item.get("ok") else "✗"
                            print(f"     {status} {item.get('item', 'N/A')}")

                    print(f"\n   💡 PM Agent 建议:")
                    print(f"      需要人工审批，切换到 Gate Session")
                    print(f"      使用命令: api_gate_show('.', '{gate['id']}')")

                    # 在自动模式下，模拟审批
                    print(f"\n   🔧 [自动模式] 模拟审批...")
                    result = api_gate_decide(
                        project_dir=self.project_dir,
                        gate_id=gate['id'],
                        option="approve",
                        comment="[自动测试] PM Agent 模拟审批通过",
                        decided_by="pm_agent_auto"
                    )

                    if "error" not in result:
                        print(f"   ✅ 模拟审批成功")
                        self.log_decision(
                            gate['id'],
                            "approve",
                            "自动模式模拟审批"
                        )
                    else:
                        print(f"   ❌ 审批失败: {result.get('error')}")

                continue  # 审批后重新检查状态

            # 5. 执行决策
            if analysis["recommendation"] == "execute_next":
                ready_steps = api_list_ready_steps(self.project_dir)

                if not ready_steps:
                    print("\n⚠️  没有就绪步骤，工作流可能阻塞")
                    break

                # 选择第一个就绪步骤
                step_to_execute = ready_steps[0]
                step_id = step_to_execute['id']

                print(f"\n💡 PM Agent 决策:")
                print(f"   执行步骤: {step_id}")
                print(f"   描述: {step_to_execute.get('description', 'N/A')}")
                print(f"   依赖: {step_to_execute.get('dependencies', [])}")

                self.log_decision(
                    step_id,
                    "execute",
                    f"就绪步骤，自动执行"
                )

                # 执行步骤
                print(f"\n⏳ 正在执行...")
                result = await api_run_step_async(self.project_dir, step_id)

                # 处理结果
                if result["status"] == "completed":
                    print(f"\n✅ 步骤完成: {step_id}")
                    print(f"   耗时: {result.get('duration_seconds', 0):.2f} 秒")
                    print(f"   引擎: {result.get('engine_type', 'unknown')}")

                    if "outputs" in result and result["outputs"]:
                        print(f"   输出文件: {len(result['outputs'])} 个")
                        for output in result["outputs"][:3]:  # 只显示前3个
                            print(f"     - {output}")

                elif result["status"] == "failed":
                    print(f"\n❌ 步骤失败: {step_id}")
                    print(f"   错误: {result.get('error', 'Unknown error')}")

                    # PM Agent 决策：是否重试
                    print(f"\n💡 PM Agent 决策:")
                    print(f"   步骤失败，但继续执行下一步（演示模式）")

                    self.log_decision(
                        step_id,
                        "continue_on_failure",
                        "演示模式，继续执行"
                    )

                else:
                    print(f"\n⚠️  步骤状态: {result['status']}")

            elif analysis["recommendation"] == "handle_failure":
                print(f"\n⚠️  有失败步骤需要处理")
                # 在实际使用中，这里需要更复杂的决策逻辑
                break

            else:
                print(f"\n⚠️  未知情况: {analysis['recommendation']}")
                break

            # 短暂延迟，便于观察
            await asyncio.sleep(0.5)

        # 最终总结
        self.print_summary()

    def print_summary(self):
        """打印执行总结"""
        self.print_section("📊 执行总结")

        print(f"\n📝 决策历史 (共 {len(self.decision_log)} 条):")
        for i, log in enumerate(self.decision_log, 1):
            print(f"\n{i}. [{log['timestamp']}]")
            print(f"   步骤: {log['step_id']}")
            print(f"   动作: {log['action']}")
            print(f"   理由: {log['reason']}")

        final_state = api_get_state(self.project_dir)
        print(f"\n📈 最终状态:")
        print(f"   完成: {final_state.get('completed_steps', 0)}/{final_state.get('total_steps', 0)}")
        print(f"   失败: {final_state.get('failed_steps', 0)}")


async def main():
    """主函数"""
    print("\n" + "🎯" * 35)
    print("  PM Agent 运行 STG 工作流示例")
    print("🎯" * 35)

    # STG 部门工作流目录
    project_dir = str(PROJECT_ROOT / "spec-global" / "departments" / "stg")

    # 创建 PM Agent
    pm_agent = STGWorkflowPM(project_dir)

    # 运行工作流
    await pm_agent.run_workflow_interactive()

    print("\n" + "=" * 70)
    print("✅ 示例完成")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
    except Exception as e:
        print(f"\n\n❌ 执行异常: {e}")
        import traceback
        traceback.print_exc()
