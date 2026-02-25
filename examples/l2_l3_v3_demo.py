"""
L2/L3 v3 Workflow Structure Demo
==================================

演示 L2 v3 工作流的结构和执行流程：
1. 研发冻结包（Frozen Dev Package）- L2 的标准输入
2. L2 v3 实例格式（kind=l2_workflow_instance）
3. complexity=M 时 spawn L3 子工作流
4. L3 v3 6 步 TDD 流程

功能：跑步记录页新增备注输入框

Usage:
    python l2_l3_v3_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_info(msg: str):
    """打印信息"""
    print(f"{Colors.CYAN}ℹ {msg}{Colors.ENDC}")


def print_success(msg: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")


def print_error(msg: str):
    """打印错误消息"""
    print(f"{Colors.RED}✗ {msg}{Colors.ENDC}")


def section_1_frozen_dev_package():
    """1. 研发冻结包 - L2 的标准输入"""
    print_section("1. 研发冻结包（Frozen Dev Package）")

    print_success("L2 工作流的标准输入：研发冻结包")
    print("""
# frozen-dev-package-running-notes.yaml
contract_type: frozen-dev-package
contract_version: "1.0"
metadata:
  package_id: FPKG-20260224-001
  created_at: "2026-02-24T10:00:00Z"
  total_confidence_score: 85

package_content:
  prd_ref: ".workflow/outputs/prd/frozen-detailed-prd-running-notes.yaml"
  tech_ref: ".workflow/outputs/stg/frozen-tech-arch-running-notes.yaml"
  ui_ref: ".workflow/outputs/ui/frozen-ui-prototype-running-notes.yaml"

scheduling_validation:
  q1_non_goals: "不做备注编辑历史、不做备注分享功能"
  q2_simplification: "先实现纯文本输入，富文本编辑器延后"
  q3_uncertainties: "长文本备注的本地存储性能可能需要优化"
  q4_ui_priority: "输入框和保存按钮必须完成，字数统计可后补"
  q5_cut_sequence: "先砍字数统计，再砍备注导出"
""")

    print_info("研发冻结包包含三个核心契约:")
    print("  • prd_ref: 冻结 PRD（由 PRD 部门产出）")
    print("  • tech_ref: 冻结技术架构（由 Stg 部门产出）")
    print("  • ui_ref: 冻结 UI 原型（由 UI 部门产出）")
    print("\n  + 5 问调度验证（scheduling_validation）")
    print("    用于风险预判和范围管理")


def section_2_l2_v3_workflow_structure():
    """2. L2 v3 工作流结构"""
    print_section("2. L2 v3 工作流结构")

    print_success("L2 v3 工作流 YAML 结构")
    print("""
kind: l2_workflow_instance    # v3 新增：标识 L2 实例
version: "3.0"
id: l2-running-notes-feature-v3
name: 跑步记录页新增备注输入框
template_id: template.dev.feature_l2_v3
level: department
status: pending

# 研发冻结包输入（核心）
frozen_dev_package:
  package_id: FPKG-20260224-001
  package_content:
    prd_ref: "path/to/frozen-detailed-prd.yaml"
    tech_ref: "path/to/frozen-tech-arch.yaml"
    ui_ref: "path/to/frozen-ui-prototype.yaml"
  scheduling_validation:
    q1_non_goals: "不做备注编辑历史"
    # ... 其他 4 问

# 上下文配置
context:
  project: "HealthTracker"
  module: "running-logs"
  repos:
    - id: "healthtracker-frontend"
      type: "frontend"
      language: "vue"

# L2 阶段定义
phases:
  - id: p1_contract_design
    name: "契约设计阶段"
    complexity: S              # v3 新增：复杂度配置
    spawns_l3: false           # v3 新增：是否 spawn L3
    depends_on: []

  - id: p2_1_fe_development
    name: "前端开发"
    complexity: M              # M = spawn 单个 L3
    spawns_l3: true            # 将 spawn L3 子工作流
    depends_on: ["p1_contract_design"]
""")

    print_info("v3 新增字段:")
    print("  • frozen_dev_package: 研发冻结包输入（替代简单的 name/prd_path）")
    print("  • kind: l2_workflow_instance（标识实例类型）")
    print("  • complexity: S/M/L（控制执行策略）")
    print("  • spawns_l3: true/false（是否派发 L3）")
    print("  • depends_on: 阶段依赖（支持并行）")


def section_3_complexity_routing():
    """3. Complexity 路由策略"""
    print_section("3. Complexity 路由策略")

    print("  L2 v3 支持 3 种 complexity 级别：\n")

    print(f"  {Colors.YELLOW}S (Simple){Colors.ENDC} - 直接执行")
    print("    ├─ 不 spawn L3")
    print("    ├─ 直接执行阶段步骤")
    print("    └─ 适用于：简单阶段（如冒烟测试）")

    print(f"\n  {Colors.YELLOW}M (Medium){Colors.ENDC} - Spawn 单个 L3")
    print("    ├─ spawn 单个 L3 子工作流")
    print("    ├─ L3 使用 6 步 TDD 流程")
    print("    └─ 适用于：中等复杂度功能")

    print(f"\n  {Colors.YELLOW}L (Large){Colors.ENDC} - PMA 拆分 + 多个 L3")
    print("    ├─ 使用 PM Agent 拆分成多个功能点")
    print("    ├─ 每个功能点 spawn 一个 L3")
    print("    ├─ 支持并行执行（基于依赖）")
    print("    └─ 适用于：大型复杂功能")


def section_4_l3_v3_6_step_flow():
    """4. L3 v3 6 步 TDD 流程"""
    print_section("4. L3 v3 6 步 TDD 流程")

    print_success("L3 v3 模板：6 步 TDD 流程\n")

    steps = [
        ("1. align_requirement", "对齐需求", "分析 Feature Spec，明确功能点与验收标准"),
        ("2. design_tests", "设计测试", "根据功能点设计测试用例（测试先行）"),
        ("3. implement", "实现", "编写实现代码使测试通过"),
        ("4. run_tests", "测试", "运行单元测试，确认所有测试通过"),
        ("5. code_review", "Review", "代码自检与评审"),
        ("6. retrospective", "复盘", "任务复盘与总结（可选）"),
    ]

    for step_id, step_name, description in steps:
        mandatory = "必须" if step_id != "6. retrospective" else "可选"
        print(f"  {Colors.GREEN}{step_id}{Colors.ENDC}: {step_name}")
        print(f"      └─ {description}")
        print(f"      └─ [{mandatory}]")

    print("\n  TDD 特点：")
    print("    └─ 测试先行（第 2 步先写测试，第 3 步再实现）")
    print("    └─ 快速反馈（每步都有明确输出）")
    print("    └─ 质量保证（代码评审 + 测试覆盖）")


def section_5_execution_flow():
    """5. 执行流程演示"""
    print_section("5. L2 → L3 执行流程")

    print_success("跑步记录页备注功能 - L2 → L3 执行流程\n")

    print("  L2 Workflow: l2-running-notes-feature-v3")
    print("  " + "─" * 56)

    phases = [
        ("p1_contract_design", "契约设计", "S", "直接执行", [
            "设计备注 API 契约",
            "输出: api-contract.yaml"
        ]),
        ("p2_1_fe_development", "前端开发", "M", "spawn L3", [
            "→ Spawn L3: l3-p2_1_fe_running_notes",
            "  1. align_requirement: 对齐需求",
            "  2. design_tests: 设计测试用例",
            "  3. implement: 实现备注输入框",
            "  4. run_tests: 运行单元测试",
            "  5. code_review: 代码评审",
            "  6. retrospective: 复盘",
            "输出: NoteInput.vue + 测试"
        ]),
        ("p2_2_be_development", "后端开发", "S", "直接执行", [
            "实现备注 API",
            "输出: API 代码"
        ]),
        ("p3_integration", "集成测试", "S", "直接执行", [
            "前后端联调",
            "输出: 集成测试报告"
        ]),
        ("p4_smoke", "冒烟测试", "S", "直接执行", [
            "端到端测试",
            "输出: 冒烟测试报告"
        ]),
    ]

    for phase_id, phase_name, complexity, action, details in phases:
        color = Colors.YELLOW if complexity == "M" else Colors.CYAN
        print(f"\n  {color}▶ {phase_id}{Colors.ENDC}: {phase_name}")
        print(f"      complexity={complexity}, action={action}")
        for detail in details:
            print(f"      • {detail}")


def section_6_parallel_execution():
    """6. 并行执行支持"""
    print_section("6. 并行执行支持")

    print_success("L2 v3 支持阶段并行执行\n")

    print("  示例：前端 + 后端并行开发\n")

    print("     p1_contract_design (完成)")
    print("              ↓")
    print("     ┌────────┴────────┐")
    print("     ▼                 ▼")
    print("  p2_1_fe_dev      p2_2_be_dev")
    print("  (前端, M)        (后端, S)")
    print("  spawn L3         直接执行")
    print("  (可并行)         (可并行)")
    print("     │                 │")
    print("     └────────┬────────┘")
    print("              ▼")
    print("     p3_integration (集成测试)")

    print("\n  并行条件：")
    print("    • depends_on 依赖已满足")
    print("    • 无共享资源冲突")


def section_7_progress_tracking():
    """7. 进度追踪 API"""
    print_section("7. 进度追踪 API")

    print_success("L2 进度追踪\n")

    print("  API: await orchestrator.get_l2_progress(workflow_id)")
    print("""
  返回数据结构:
  {
    "workflow_id": "l2-running-notes-feature-v3",
    "status": "running",
    "progress_percent": 40,        # 阶段完成百分比
    "phases": {
      "total": 5,                  # 总阶段数
      "completed": 2,              # 已完成
      "running": 1,                # 运行中
      "pending": 2                 # 待处理
    },
    "l3_instances": {
      "total": 1,                  # L3 总数
      "completed": 0,              # 已完成 L3
      "pending": 1                 # 待处理 L3
    },
    "phase_details": [
      {"id": "p1", "status": "completed", "complexity": "S", "l3_count": 0},
      {"id": "p2_1_fe", "status": "running", "complexity": "M", "l3_count": 1},
      ...
    ]
  }
""")


def section_8_event_bus():
    """8. 事件总线"""
    print_section("8. 事件总线集成")

    print_success("L2/L3 生命周期事件\n")

    from lee.orchestrator.core.event_bus import EventType

    events = [
        (EventType.L2_PHASE_STARTED.value, "L2 阶段开始", {"workflow_id", "phase_id", "complexity"}),
        (EventType.L2_PHASE_COMPLETED.value, "L2 阶段完成", {"workflow_id", "phase_id", "l3_count"}),
        (EventType.L3_SPAWNED.value, "L3 子工作流派发", {"parent_l2_id", "phase_id", "l3_id", "point_id"}),
        (EventType.PMA_SPLIT_COMPLETED.value, "PMA 拆分完成", {"workflow_id", "phase_id", "point_count"}),
        (EventType.L3_COMPLETED.value, "L3 子工作流完成", {"l3_id", "status"}),
    ]

    for event_type, event_name, payload_fields in events:
        print(f"  {Colors.GREEN}{event_type}{Colors.ENDC}")
        print(f"      └─ {event_name}")
        print(f"      └─ payload: {', '.join(payload_fields)}")


def section_9_file_structure():
    """9. 文件结构"""
    print_section("9. 文件结构")

    print_success("L2/L3 v3 文件组织\n")

    print("""
# 框架模板目录 (版本控制管理)
lee/spec-global/departments/dev/workflows/
├── templates/
│   ├── l3/
│   │   └── task-l3-v3-template.yaml      # L3 v3 模板（6 步）
│   └── feature-l2-template.yaml          # L2 模板
└── feature/
    ├── v2/
    │   └── workflow.yaml                 # L2 v2 工作流
    └── v3/
        └── workflow.yaml                 # L2 v3 工作流（新增）

# 运行时目录 (运行时生成，.gitignore)
.workflow/
├── inputs/                               # 输入文件
│   └── frozen-dev-package-running-notes.yaml  # 研发冻结包
└── instances/                            # 运行时实例目录
    ├── l2/                               # L2 实例
    │   └── l2-v3/
    │       └── running-notes-feature.yaml # L2 v3 实例（运行时生成）
    └── l3/                               # L3 实例
        └── l3-v3/
            └── p2_1_fe_development.yaml   # L3 v3 实例（运行时生成）

examples/
└── l2_l3_v3_demo.py                      # v3 演示脚本
""")


def section_10_code_changes():
    """10. 代码改动总结"""
    print_section("10. v3 改造 - 代码改动总结")

    print_success("新增文件\n")

    files = [
        ("lee/spec-global/departments/dev/workflows/feature/v3/workflow.yaml",
         "L2 v3 工作流模板"),
        ("lee/spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml",
         "L3 v3 模板（6 步 TDD 流程）"),
        (".workflow/instances/l2/l2-v3/running-notes-feature.yaml",
         "L2 v3 实例（运行时生成）"),
        (".workflow/instances/l3/l3-v3/p2_1_fe_development.yaml",
         "L3 v3 实例（运行时生成）"),
        ("examples/l2_l3_v3_demo.py",
         "v3 演示脚本"),
    ]

    for file_path, description in files:
        print(f"  {Colors.GREEN}+{Colors.ENDC} {file_path}")
        print(f"      └─ {description}")

    print("\n" + Colors.CYAN + "修改文件" + Colors.ENDC + "\n")

    modified_files = [
        ("src/lee/orchestrator/execution/orchestrator.py",
         "_spawn_l3_for_point() - 使用 L3 v3 模板，发布事件"),
    ]

    for file_path, changes in modified_files:
        print(f"  {Colors.YELLOW}~{Colors.ENDC} {file_path}")
        print(f"      └─ {changes}")


async def main():
    """主函数"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   L2/L3 v3 Workflow Structure Demo                       ║")
    print("║   跑步记录页新增备注输入框功能                              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")

    # 运行各个演示部分
    section_1_frozen_dev_package()
    section_2_l2_v3_workflow_structure()
    section_3_complexity_routing()
    section_4_l3_v3_6_step_flow()
    section_5_execution_flow()
    section_6_parallel_execution()
    section_7_progress_tracking()
    section_8_event_bus()
    section_9_file_structure()
    section_10_code_changes()

    # 总结
    print_section("Demo 总结")
    print_success("L2/L3 v3 工作流改造完成")
    print("\n  关键特性:")
    print("    ✓ 研发冻结包作为 L2 标准输入")
    print("    ✓ L2 v3 实例格式 (kind=l2_workflow_instance)")
    print("    ✓ complexity=M 时 spawn L3 子工作流")
    print("    ✓ L3 v3 6 步 TDD 流程")
    print("    ✓ 阶段依赖与并行执行")
    print("    ✓ 进度追踪 API")
    print("    ✓ 事件总线集成")

    print("\n  下一步:")
    print("    • 准备研发冻结包（frozen-dev-package.yaml）")
    print("    • 运行实际工作流: python -m lee.orchestrator.cli run l2-running-notes-feature-v3")
    print("    • 查看进度: await orchestrator.get_l2_progress('l2-id')")
    print("    • 监听事件: event_bus.subscribe(EventType.L3_SPAWNED, handler)")


if __name__ == "__main__":
    asyncio.run(main())
