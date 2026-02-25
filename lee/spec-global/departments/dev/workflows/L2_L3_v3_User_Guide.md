# L2/L3 v3 工作流使用说明

**版本**: v3.0
**更新日期**: 2026-02-24
**适用范围**: Dev 部门特性开发流程

---

## 目录

1. [概述](#概述)
2. [核心概念](#核心概念)
3. [研发冻结包](#研发冻结包)
4. [L2 工作流](#l2-工作流)
5. [L3 工作流](#l3-工作流)
6. [使用流程](#使用流程)
7. [实例配置](#实例配置)
8. [执行监控](#执行监控)
9. [文件结构](#文件结构)
10. [常见问题](#常见问题)

---

## 概述

L2/L3 v3 工作流是 Dev 部门的特性开发流程，支持：

- **L2（部门级）**: 管理特性的完整开发流程
- **L3（任务级）**: 执行具体的开发任务
- **Complexity 路由**: 根据任务复杂度自动选择执行策略
- **6 步 TDD**: 测试驱动的开发流程

### v3 新特性

| 特性 | 说明 |
|------|------|
| `kind` 标识 | 区分模板和实例 |
| `complexity` 配置 | S/M/L 三级复杂度 |
| L3 Spawning | complexity=M 时自动派发 L3 |
| 6 步 TDD 流程 | 对齐需求→设计测试→实现→测试→review→复盘 |
| 阶段并行 | 前后端可并行开发 |

---

## 核心概念

### L2 vs L3

```
┌─────────────────────────────────────────────────────────────┐
│  L2 Workflow (部门级)                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 契约设计  │→ │ 并行开发  │→ │ 集成测试  │→ │ 冒烟测试  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                      ↓                                     │
│              complexity=M 时 spawn L3                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  L3 Workflow (任务级) - 6 步 TDD                           │
│  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐               │
│  │对齐│→ │设计│→ │实现│→ │测试│→ │Review│→ │复盘│          │
│  │需求 │  │测试│  │    │  │    │  │    │  │    │          │
│  └───┘  └───┘  └───┘  └───┘  └───┘  └───┘               │
│  [必须] [必须] [必须] [必须] [必须] [可选]                 │
└─────────────────────────────────────────────────────────────┘
```

### Complexity 级别

| 级别 | 名称 | 执行策略 | 适用场景 |
|------|------|----------|----------|
| **S** | Simple | 直接执行阶段步骤 | 简单任务、测试 |
| **M** | Medium | Spawn 单个 L3 | 中等复杂度功能 |
| **L** | Large | PMA 拆分 → 多个 L3 | 大型复杂功能 |

---

## 研发冻结包

L2 工作流的标准输入是**研发冻结包 (Frozen Dev Package)**，而非简单的名称或 PRD 文件路径。研发冻结包是一个完整的研发输入契约，确保开发团队获得充分的信息。

### 结构

```yaml
contract_type: frozen-dev-package
contract_version: "1.0"
metadata:
  package_id: FPKG-20260224-001
  created_at: "2026-02-24T10:00:00Z"
  total_confidence_score: 85

package_content:
  prd_ref: "path/to/frozen-detailed-prd.yaml"      # 冻结 PRD
  tech_ref: "path/to/frozen-technical-architecture.yaml"  # 冻结技术架构
  ui_ref: "path/to/frozen-ui-prototype.yaml"       # 冻结 UI 原型

scheduling_validation:
  q1_non_goals: "这个需求不做什么？"
  q2_simplification: "哪些地方允许先简化 / 降级？"
  q3_uncertainties: "技术上最不确定的 1～2 个点是什么？"
  q4_ui_priority: "哪些 UI 是必须现在定，哪些可以后补？"
  q5_cut_sequence: "如果延期，最先砍哪一块？"
```

### 5 问调度验证

| 问题 | 说明 | 示例 |
|------|------|------|
| Q1 | 非目标 | 明确不做哪些功能，避免范围蔓延 |
| Q2 | 简化点 | 允许先降级实现的部分，如先用默认图片 |
| Q3 | 不确定性 | 技术风险点，如第三方 API 兼容性 |
| Q4 | UI 优先级 | 核心 UI 必须完成，次要 UI 可后补 |
| Q5 | 砍序 | 延期时的砍功能顺序，如先砍统计功能 |

### 为什么需要研发冻结包？

1. **完整性**: 包含 PRD、技术架构、UI 原型三个维度的完整信息
2. **可追溯性**: 通过 `package_id` 可追踪整个研发周期
3. **风险预判**: 5 问验证帮助团队提前识别风险和简化点
4. **质量保证**: `total_confidence_score` 反映冻结包的质量水平

---

## L2 工作流

### 阶段定义

| 阶段 ID | 名称 | 默认 Complexity | 说明 |
|---------|------|-----------------|------|
| `p1_contract_design` | 契约设计 | M | API 契约设计与评审 |
| `p2_1_fe_development` | 前端开发 | M | 前端实现（spawn L3） |
| `p2_2_be_development` | 后端开发 | M | 后端实现 |
| `p3_integration` | 集成测试 | S | 前后端联调 |
| `p4_smoke` | 冒烟测试 | S | 端到端测试 |

### 阶段依赖关系

```
p1_contract_design (完成)
         ↓
    ┌────┴────┐
    ↓         ↓
p2_1_fe    p2_2_be   ← 可并行
    └────┬────┘
         ↓
   p3_integration
         ↓
      p4_smoke
```

---

## L3 工作流

### 6 步 TDD 流程

| 步骤 | 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| 1 | `align_requirement` | Agent | ✅ | 分析 Feature Spec，明确功能点 |
| 2 | `design_tests` | Agent | ✅ | 设计测试用例（测试先行） |
| 3 | `implement` | Agent | ✅ | 编写实现代码 |
| 4 | `run_tests` | Skill | ✅ | 运行单元测试 |
| 5 | `code_review` | Agent | ✅ | 代码评审 |
| 6 | `retrospective` | Agent | ❌ | 任务复盘 |

### TDD 特点

1. **测试先行**: 第 2 步先写测试，第 3 步再实现
2. **快速反馈**: 每步都有明确输出
3. **质量保证**: 代码评审 + 测试覆盖

---

## 使用流程

### 前置条件：准备研发冻结包

在启动 L2 工作流之前，需要先准备好研发冻结包。研发冻结包由 Stg/UI/PRD 部门的前置工作流产出。

```yaml
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
```

### 方式一：CLI 命令

```bash
# 1. 创建 L2 实例（指定研发冻结包）
lee workflow create \
  --template template.dev.feature_l2_v3 \
  --frozen-dev-package .workflow/inputs/frozen-dev-package-running-notes.yaml \
  --output .workflow/instances/l2/running-notes.yaml

# 2. 配置 complexity（编辑 YAML）
# 修改 phases[].complexity 为 S/M/L

# 3. 运行 L2 工作流
lee workflow run \
  --instance .workflow/instances/l2/running-notes.yaml

# 4. 查看进度
lee workflow status <workflow-id>

# 5. 查看 L3 子工作流
lee workflow list --parent <l2-id>
```

### 方式二：Python API

```python
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.sqlite_store import SQLiteStore
import yaml

# 初始化
store = SQLiteStore(db_path=".lee/workflow.db")
await store.connect()
orchestrator = Orchestrator(store=store, project_root=".")

# 加载研发冻结包
with open(".workflow/inputs/frozen-dev-package-running-notes.yaml") as f:
    frozen_dev_package = yaml.safe_load(f)

# 创建 L2 实例
l2_workflow = await orchestrator.create_workflow(
    level=WorkflowLevel.DEPARTMENT,
    template_id="template.dev.feature_l2_v3",
    data={
        "name": "跑步记录页备注功能",
        "frozen_dev_package": frozen_dev_package,  # 传入完整冻结包
        "phases": [
            {"id": "p1_contract_design", "complexity": "M"},
            {"id": "p2_1_fe_development", "complexity": "M"},  # spawn L3
            {"id": "p2_2_be_development", "complexity": "M"},
            {"id": "p3_integration", "complexity": "S"},
            {"id": "p4_smoke", "complexity": "S"},
        ]
    }
)

# 运行工作流
await orchestrator.run_workflow(l2_workflow.id)

# 等待完成
await orchestrator.wait_for_completion(l2_workflow.id)
```

---

## 实例配置

### L2 实例示例

```yaml
# .workflow/instances/l2/running-notes-feature.yaml
kind: l2_workflow_instance
version: "3.0"
id: l2-running-notes-feature
name: 跑步记录页备注功能
template_id: template.dev.feature_l2_v3
status: pending

# 研发冻结包输入（核心）
frozen_dev_package:
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

# 上下文配置
context:
  project: "HealthTracker"
  module: "running-logs"
  repos:
    - id: "healthtracker-fe"
      type: "frontend"
      language: "vue"

# 阶段配置
phases:
  - id: p1_contract_design
    name: "契约设计"
    complexity: M  # M = spawn L3
    status: pending
    l3_instance_ids: []

  - id: p2_1_fe_development
    name: "前端开发"
    complexity: M  # M = spawn L3
    status: pending
    l3_instance_ids: []

  - id: p2_2_be_development
    name: "后端开发"
    complexity: M
    status: pending
    l3_instance_ids: []

  - id: p3_integration
    name: "集成测试"
    complexity: S  # S = 直接执行
    status: pending

  - id: p4_smoke
    name: "冒烟测试"
    complexity: S
    status: pending
```

### L3 实例示例

```yaml
# .workflow/instances/l3/p2_1_fe_development.yaml
kind: l3_workflow_instance
version: "3.0"
id: l3-p2_1_fe_development
name: "L3: 前端备注输入框实现"
template_id: template.dev.task_l3_v3
status: pending

# 功能点引用
point_id: "p2_1_fe_development"
point_title: "前端备注输入框"
point_description: "实现跑步记录页的备注输入和保存功能"

# 父引用
parent_l2_id: "l2-running-notes-feature"
parent_phase_id: "p2_1_fe_development"

# 仓库配置
repo_id: "healthtracker-fe"
branch: "feature/running-notes"

# 6 步 TDD 流程
steps:
  - id: align_requirement
    name: "对齐需求"
    status: pending
    kind: agent
    mandatory: true

  - id: design_tests
    name: "设计测试"
    status: pending
    kind: agent
    mandatory: true

  - id: implement
    name: "实现"
    status: pending
    kind: agent
    mandatory: true

  - id: run_tests
    name: "测试"
    status: pending
    kind: skill
    mandatory: true

  - id: code_review
    name: "Review"
    status: pending
    kind: agent
    mandatory: true

  - id: retrospective
    name: "复盘"
    status: pending
    kind: agent
    mandatory: false
```

---

## 执行监控

### 查看 L2 进度

```python
# 获取 L2 进度
progress = await orchestrator.get_l2_progress("l2-running-notes-feature")

print(f"进度: {progress['progress_percent']}%")
print(f"阶段: {progress['phases']['completed']}/{progress['phases']['total']}")
print(f"L3: {progress['l3_instances']['completed']}/{progress['l3_instances']['total']}")
```

### 监听事件

```python
from lee.orchestrator.core.event_bus import get_event_bus, EventType

event_bus = get_event_bus()

# 监听 L3 派发事件
async def on_l3_spawned(event):
    print(f"L3 派发: {event.payload}")
    print(f"  L2 ID: {event.payload['parent_l2_id']}")
    print(f"  Phase ID: {event.payload['phase_id']}")
    print(f"  L3 ID: {event.payload['l3_id']}")

event_bus.subscribe(EventType.L3_SPAWNED, on_l3_spawned)
```

### 查看输出文件

```
.workflow/instances/
├── l2/running-notes-feature/
│   ├── output/
│   │   ├── api-contract.yaml        # P1 契约设计
│   │   ├── fe-l3-output.json        # P2.1 前端 L3 输出
│   │   ├── be-code-diff.patch       # P2.2 后端代码
│   │   ├── integration-test-report.json
│   │   └── smoke-test-report.json
│
└── l3/p2_1_fe_development/
    └── output/
        ├── p2_1_fe_development-requirement-analysis.yaml
        ├── p2_1_fe_development-test-code-diff.patch
        ├── p2_1_fe_development-code-diff.patch
        ├── p2_1_fe_development-test-report.json
        ├── p2_1_fe_development-coverage.json
        ├── p2_1_fe_development-review.json
        └── p2_1_fe_development-retrospective.md
```

---

## 文件结构

### 模板文件（框架目录）

```
lee/spec-global/departments/dev/workflows/
├── templates/
│   ├── l3/
│   │   └── task-l3-v3-template.yaml    # L3 v3 模板
│   └── feature-l2-template.yaml         # L2 基础模板
└── feature/
    └── v3/
        └── workflow.yaml                 # L2 v3 工作流
```

### 实例文件（运行时目录）

```
.workflow/                                 # .gitignore
└── instances/                             # 运行时生成
    ├── l2/                                # L2 实例
    │   ├── l2-v3/
    │   │   └── running-notes-feature.yaml
    │   └── output/
    └── l3/                                # L3 实例
        ├── l3-v3/
        │   └── p2_1_fe_development.yaml
        └── output/
```

---

## 常见问题

### Q1: 研发冻结包从哪里来？

研发冻结包是前置工作流的产出：
- **PRD 部门**: 产出 `frozen-detailed-prd`
- **Stg 部门**: 产出 `frozen-technical-architecture`
- **UI 部门**: 产出 `frozen-ui-prototype`

在启动 L2 工作流前，确保这三个冻结契约都已完成。

### Q2: 如何选择 complexity 级别？

| 场景 | 推荐 |
|------|------|
| 简单单页开发、Bug 修复 | S |
| 新功能模块、前后端联调 | M |
| 大型重构、多模块联动 | L |

### Q3: L3 失败了怎么办？

L3 失败会阻塞 L2 进度。可以：

1. 查看失败步骤的输出文件
2. 修复后重新运行该 L3
3. 或手动标记 L3 完成（需审批）

### Q4: 能否跳过某一步骤？

- L2: 可以通过 `depends_on: []` 跳过依赖
- L3: 只有 `retrospective` 是可选的，其他步骤必须执行

### Q5: 如何手动创建 L3 实例？

```bash
# 使用 WorkflowGenerator
python -c "
from lee.orchestrator.core.workflow_generator import WorkflowGenerator, L3InstanceConfig
from lee.orchestrator.storage.models import Point, Complexity

gen = WorkflowGenerator('lee/spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml')

point = Point(
    id='my-feature',
    title='My Feature',
    desc='Description',
    layer='ui',
    estimated_complexity=Complexity.M,
)

config = L3InstanceConfig(
    point=point,
    parent_l2_id='l2-xxx',
    parent_phase_id='p2_1_fe_development',
    repo_id='fe-repo',
)

result = gen.generate_l3_instance(config, '.workflow/instances/l3/my-feature.yaml')
print(f'Success: {result.success}')
"
```

### Q6: 事件监听如何使用？

参考 [执行监控](#执行监控) 章节的事件监听示例。

---

## 附录

### 相关文档

- [Dev 部门宪法](../AGENTS.md)
- [契约规范](../contracts/)
- [前端测试标准](../standards/frontend-testing/)

### 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v3.0 | 2026-02-24 | 新增 L3 v3 6 步 TDD 流程 |
| v2.0 | 2026-02-12 | L2 v2 基础流程 |

---

**文档维护**: Dev Workflow Team
**联系方式**: 见 Dev 部门宪法
