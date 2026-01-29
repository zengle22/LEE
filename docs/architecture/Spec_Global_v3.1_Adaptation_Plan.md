# Spec-Global v3.1 适配方案

> **版本**: 1.0
> **日期**: 2026-01-28
> **目标**: 将 spec-global 规范体系适配到 LEE Orchestrator v3.1 架构
> **状态**: 📋 方案草案

---

## 一、问题分析

### 1.1 当前状态

**Spec-Global (静态规范)**:
- 134 个 YAML/Markdown 规范文件
- 定义了 agents、skills、workflows、gates、contracts
- 静态定义，无运行时能力
- AI 宪法要求"必须通过 Orchestrator 执行"

**v3.1 Orchestrator (运行时系统)**:
- Core + 4 个外圈能力的运行时架构
- SQLite 作为唯一状态权威
- 统一的三层数据模型 (L1/L2/L3)
- EventBus、StateMachine、TemplateManager 等运行时组件

### 1.2 核心矛盾

```
┌─────────────────────────────────────────────────────────────┐
│                    当前架构脱节                               │
├─────────────────────────────────────────────────────────────┤
│  Spec-Global (静态)                    v3.1 (运行时)         │
│  ├── workflow.yaml (静态定义)      ──✕──  WorkflowTemplate  │
│  ├── agent.yaml (规范定义)        ──✕──  Agent 引用         │
│  ├── gate.yaml (门禁定义)         ──✕──  Human Gate 机制    │
│  └── contract (契约定义)          ──✕──  验证器系统         │
└─────────────────────────────────────────────────────────────┘
```

**问题**:
1. Spec-Global 的 workflow.yaml 无法被 v3.1 TemplateManager 加载
2. Agent 定义格式与 v3.1 的 Agent 系统不兼容
3. Gate 机制与 v3.1 的状态机不集成
4. Contract 验证未对接 v3.1 的验证器系统

---

## 二、适配方案总览

### 2.0 目录层级约定（L1/L2/L3 与物理目录的映射）

**核心原则**：
- **物理目录结构 = Scope / 参与边界**
- **metadata.owner = 组织责任人**

| 层级 | v3.1 level | 物理目录位置 | workflow_id 命名 | 所有权（owner） |
|------|-----------|-------------|-----------------|---------------|
| **L1** | `project` | `cross/workflows/project/` | `workflow.cross.*` | 可选（如 `departments/office`） |
| **L2** | `department` | `departments/{dept}/workflows/` | `workflow.{dept}.*` | 该部门自身 |
| **L3（跨部门）** | `task` | `cross/workflows/task/` | `workflow.cross.task.*` | 跨部门共享 |
| **L3（部门内）** | `task` | `departments/{dept}/workflows/` 下的子目录 | `workflow.{dept}.task.*` | 所属部门 |

**L1（项目级 / 公司级）workflow 放置规则**：

> **L1 workflow 统一放在 `cross/workflows/project/`，而不是某个部门（包括 office），也不用单独拉 `projects/` 新模块。**

**原因**：
1. **语义清晰**：真正的 L1 一定是"跨部门"的主流程，不应归在任何单一部门名下
2. **避免混淆**：若放在 `departments/office/workflows/`，会让人误以为"项目主流程是 office 部门的内部流程"
3. **权力分离**：组织责任（owner）与结构边界（目录）分离，符合 LEE 一贯的"权力结构独立于物理结构"思路

**Cross 二级目录结构（防止 L1/L3 混淆）**：

> **cross 表示"跨部门"，不是"L1 专用"。在 `cross/workflows` 下按 level 再分一层：**

```text
cross/
  workflows/
    project/              # L1：项目级 / 产品级主流程
      product-pipeline/v1/workflow.yaml
      research-initiative/v1/workflow.yaml
      ai-running-coach/v1/workflow.yaml

    task/                 # L3：跨部门任务型 workflow
      bugfix-critical/v1/workflow.yaml
      create-product-brief/v1/workflow.yaml
      run-user-interview/v1/workflow.yaml

    lib/                  # 可选：可复用子流程 / fragment
      common-review-stage/v1/workflow.yaml
```

**几条简单记忆规则**：
1. **凡是 L1（project 级）→ 一律放 `cross/workflows/project/`**
2. **凡是跨部门但不是大项目主链路、而是一类"可被调用的任务" → 放 `cross/workflows/task/`**
3. **某个部门自己的小任务 → 放 `departments/{dept}/workflows/` 下的子目录**

**所有权表达**（通过 metadata，不通过目录）：

```yaml
# spec-global/_metadata.yaml
workflow_registry:
  # L1（Project 级）- 统一放在 cross/workflows/project/
  - id: workflow.cross.product_pipeline
    path: cross/workflows/project/product-pipeline/v1/workflow.yaml
    level: project
    owner: "departments/office"   # PMO 是 owner，但 scope 仍然是 cross

  # 跨部门 L3（Task 级）- 放在 cross/workflows/task/
  - id: workflow.cross.task.create_product_brief
    path: cross/workflows/task/create-product-brief/v1/workflow.yaml
    level: task
    # owner 可选，跨部门共享任务通常不需要指定 owner
```

**一句话记忆版**：
- **跨部门主链路 → `cross/workflows/project/`（L1）**
- **部门内流水线 → `departments/*/workflows/`（L2）**
- **跨部门任务工具 → `cross/workflows/task/`（L3）**
- **部门内任务 → `departments/*/workflows/` 下的子目录（L3）**

### 2.0.1 L1/L2 串联模型（跨部门协作模式）

**核心设计**：L1 编排层串联多个 L2 执行层

```
┌─────────────────────────────────────────────────────────────┐
│  L1 (Project 级) - 跨部门主链路                              │
│  workflow.cross.product_delivery_pipeline                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  负责编排：PRD 部门 → Dev 部门 → QA 部门 → ...      │    │
│  │  定义交接规则、数据流转、Gate 协调                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐    │
│  │ L2: PRD 部门流水线    │ ───→ │ L2: Dev 部门流水线    │    │
│  │ 产出: 研发冻结包      │      │ 输入: 研发冻结包      │    │
│  └──────────────────────┘      └──────────────────────┘    │
│           │                              │                  │
│           ↓                              ↓                  │
│  「PRD → Dev 交接」的 L1 编排逻辑                              │
└─────────────────────────────────────────────────────────────┘
```

**关键原则**：

1. **L2 是专业执行层**（部门内流程）
   - 各自负责部门内的专业流程
   - 输出标准化的"冻结包"或"契约产物"
   - L2 之间**不直接串联**，保持独立性

2. **L1 是编排层**（跨部门主链路）
   - 串联多个 L2 流水线
   - 定义交接规则和数据流转
   - 协调跨部门的 Gate 和状态

3. **数据流转方式**
   - L2 输出 → Artifact Store（SQLite）
   - L1 从 Artifact Store 读取 → 传递给下一个 L2
   - L1 通过 `spawn_workflow()` 触发子 L2

**示例：PRD → Dev 串联**

```yaml
# L1: workflow.cross.product_delivery_pipeline
stages:
  - stage: s1_prd_delivery
    steps:
      - id: s1_1_trigger_prd_pipeline
        run: spawn_workflow(
          level: department,
          template_id: workflow.prd.product_to_dev_pipeline,
          input: { product_requirements: "..." }
        )
        # 等待 PRD L2 完成，产出研发冻结包
      - id: s1_2_verify_freeze_package
        gate: h1_freeze_package_review  # L1 级别的 Gate

  - stage: s2_dev_execution
    steps:
      - id: s2_1_trigger_dev_pipeline
        run: spawn_workflow(
          level: department,
          template_id: workflow.dev.development_pipeline,
          input: { freeze_package: "$$artifact.from_s1_1" }  # 引用 L2 产物
        )
        # 等待 Dev L2 完成
      - id: s2_2_product_acceptance
        gate: h2_product_acceptance  # L1 级别的验收 Gate
```

**目录映射总结**：

| 层级 | 作用 | 物理目录 | 命名规则 | 示例 |
|------|------|----------|---------|------|
| L1 | 编排多个 L2，定义跨部门协作 | `cross/workflows/project/` | `workflow.cross.*` | `workflow.cross.product_delivery_pipeline` |
| L2 | 部门内专业流程，产出标准产物 | `departments/{dept}/workflows/` | `workflow.{dept}.*` | `workflow.prd.product_to_dev_pipeline` |
| L3（跨部门） | 跨部门共享的任务型 workflow | `cross/workflows/task/` | `workflow.cross.task.*` | `workflow.cross.task.bugfix_critical` |
| L3（部门内） | 部门内任务，可被 L2 spawn | `departments/{dept}/workflows/` 下的子目录 | `workflow.{dept}.task.*` | `workflow.dev.phase_openspec_flow` |

### 2.1 目标架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    v3.1 + Spec-Global 融合架构                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │               Spec-Global 规范层 (声明式)                           │  │
│  │  ├── agents/        - Agent 能力定义                                │  │
│  │  ├── workflows/     - 工作流定义                                    │  │
│  │  ├── gates/         - 门禁定义                                      │  │
│  │  ├── contracts/     - 契约定义                                      │  │
│  │  └── skills/        - 技能定义                                      │  │
│  └───────────────────────────┬───────────────────────────────────────┘  │
│                              │ Loader (v3.1 新增)                       │
│                              ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │            v3.1 运行时层 (命令式)                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │  │  Core                                                       │   │  │
│  │  │  ├── TemplateManager  ← 加载 spec-global/workflows/          │   │  │
│  │  │  ├── StateMachine      ← 集成 spec-global/gates/             │   │  │
│  │  │  └── Orchestrator     ← 核心调度                              │   │  │
│  │  └─────────────────────────────────────────────────────────────┘   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │  │  四个外圈能力 (v3.1)                                         │   │  │
│  │  │  ├── Agent 系统       ← 加载 spec-global/agents/              │   │  │
│  │  │  ├── 可观测性系统    ← 执行追踪                               │   │  │
│  │  │  ├── 验证器系统      ← 加载 spec-global/contracts/            │   │  │
│  │  │  └── 工作流工程      ← 转换 workflow.yaml                     │   │  │
│  │  └─────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │            SQLite (唯一状态权威)                                    │  │
│  │  ├── workflow_instances  ← L1/L2/L3 统一模型                      │  │
│  │  ├── task_executions     ← 步骤执行记录                            │  │
│  │  └── events              ← EventBus 事件日志                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

1. **声明式规范 + 命令式运行时**
   - Spec-Global 保持声明式定义（"做什么"）
   - v3.1 提供命令式执行（"怎么做"）

2. **双向兼容**
   - Spec-Global 规范可被 v3.1 加载
   - v3.1 运行时可回溯到 Spec-Global 定义

3. **最小侵入**
   - Spec-Global 目录结构不变
   - 新增 Loader 层做转换
   - v3.1 核心架构不变

4. **渐进迁移**
   - 支持同时运行旧 workflow 和新 workflow
   - 逐步迁移 134 个规范文件

---

## 三、详细改造方案

### 3.1 工作流工程改造 (Workflow Engineering)

#### 3.1.1 WorkflowLoader 新增

**文件**: `src/lee/orchestrator/core/workflow_loader.py` (新增)

```python
"""
WorkflowLoader - 从 spec-global 加载工作流定义

职责：
1. 扫描 spec-global/{scope}/workflows/ 目录
2. 解析 workflow.yaml 文件
3. 转换为 v3.1 的 WorkflowTemplate 格式
4. 注册到 TemplateManager
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from lee.orchestrator.core.template_manager import WorkflowTemplate, Step


@dataclass
class SpecGlobalWorkflow:
    """Spec-Global workflow 原始格式"""
    id: str
    version: str
    name: str
    description: str
    kind: str  # "workflow" or "workflow-instance"
    stages: List[Dict]
    human_in_the_loop: List[Dict]
    completion: Dict
    tests: Dict


class WorkflowLoader:
    """从 spec-global 加载工作流"""

    def __init__(self, spec_global_root: Path):
        self.spec_global_root = spec_global_root
        self.workflows_dir = spec_global_root / "workflows"

    def scan_workflows(self) -> Dict[str, SpecGlobalWorkflow]:
        """扫描所有 workflow.yaml 文件

        扫描范围（按目录层级约定）：
        - L1（Project 级）: cross/workflows/project/ → workflow.cross.*
        - L2（Department 级）: departments/{dept}/workflows/ → workflow.{dept}.*
        - L3（跨部门 Task 级）: cross/workflows/task/ → workflow.cross.task.*
        - L3（部门内 Task 级）: departments/{dept}/workflows/ 下的子目录 → workflow.{dept}.task.*
        """
        workflows = {}

        # 扫描 L1（Project 级）: cross/workflows/project/
        project_dir = self.spec_global_root / "cross" / "workflows" / "project"
        if project_dir.exists():
            for yaml_file in project_dir.rglob("workflow.yaml"):
                workflow = self._load_workflow_yaml(yaml_file)
                workflows[workflow.id] = workflow

        # 扫描 L3（跨部门 Task 级）: cross/workflows/task/
        task_dir = self.spec_global_root / "cross" / "workflows" / "task"
        if task_dir.exists():
            for yaml_file in task_dir.rglob("workflow.yaml"):
                workflow = self._load_workflow_yaml(yaml_file)
                workflows[workflow.id] = workflow

        # 扫描 L2/L3（Department/Task 级）: departments/{dept}/workflows/
        for dept_dir in (self.spec_global_root / "departments").iterdir():
            workflows_path = dept_dir / "workflows"
            if workflows_path.exists():
                for yaml_file in workflows_path.rglob("workflow.yaml"):
                    workflow = self._load_workflow_yaml(yaml_file)
                    workflows[workflow.id] = workflow

        return workflows

    def _validate_layout_consistency(
        self,
        workflow_id: str,
        path: str,
        level: str
    ) -> None:
        """校验目录布局与 level 的一致性

        规则：
        - level = project → path 必须包含 cross/workflows/project/
        - level = task 且 id 以 workflow.cross.task. 开头 → path 必须包含 cross/workflows/task/
        - level = department → path 必须包含 departments/<dept>/workflows/

        Raises:
            ValueError: 当布局不一致时
        """
        path_normalized = path.replace("\\", "/")

        if level == "project":
            if "cross/workflows/project/" not in path_normalized:
                raise ValueError(
                    f"Workflow {workflow_id} has level=project, "
                    f"but path is not in cross/workflows/project/: {path}"
                )

        elif level == "task":
            if workflow_id.startswith("workflow.cross.task."):
                if "cross/workflows/task/" not in path_normalized:
                    raise ValueError(
                        f"Workflow {workflow_id} is a cross-department task, "
                        f"but path is not in cross/workflows/task/: {path}"
                    )
            # department 内的 task 没有强制路径约束

        elif level == "department":
            if "departments/" not in path_normalized or "/workflows/" not in path_normalized:
                raise ValueError(
                    f"Workflow {workflow_id} has level=department, "
                    f"but path is not in departments/<dept>/workflows/: {path}"
                )

    def _load_workflow_yaml(self, yaml_path: Path) -> SpecGlobalWorkflow:
        """加载单个 workflow.yaml"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return SpecGlobalWorkflow(
            id=data.get('id', ''),
            version=data.get('version', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            kind=data.get('kind', 'workflow'),
            stages=data.get('stages', []),
            human_in_the_loop=data.get('human_in_the_loop', []),
            completion=data.get('completion', {}),
            tests=data.get('tests', {}),
        )

    def convert_to_template(
        self,
        workflow: SpecGlobalWorkflow
    ) -> WorkflowTemplate:
        """将 Spec-Global workflow 转换为 v3.1 WorkflowTemplate"""

        # 提取 steps (扁平化 stages)
        steps = []
        for stage in workflow.stages:
            stage_steps = self._extract_steps_from_stage(stage)
            steps.extend(stage_steps)

        # 提取 gates (human_in_the_loop → gates)
        gates = self._extract_gates(workflow.human_in_the_loop)

        # 构造 WorkflowTemplate
        return WorkflowTemplate(
            id=workflow.id,
            name=workflow.name,
            version=workflow.version,
            description=workflow.description,
            steps=steps,
            gates=gates,
            # 新增：spec_global_source 追溯
            metadata={
                'spec_global_kind': workflow.kind,
                'source_type': 'spec_global',
            }
        )

    def _extract_steps_from_stage(self, stage: Dict) -> List[Step]:
        """从 stage 提取 steps"""
        steps = []

        for step_def in stage.get('steps', []):
            # 提取 executor_type
            executor_type = self._infer_executor_type(step_def)

            # 提取依赖
            dependencies = step_def.get('dependencies', {})
            requires = dependencies.get('requires', [])

            # 提取 gates
            step_gates = step_def.get('human_gate', None)

            step = Step(
                id=step_def.get('id', ''),
                name=step_def.get('name', ''),
                description=step_def.get('description', ''),
                executor_type=executor_type,
                dependencies=requires,
                gates=step_gates,
                input=step_def.get('inputs', {}),
                output=step_def.get('outputs', {}),
                on_error=step_def.get('on_error', {}),
            )
            steps.append(step)

        return steps

    def _infer_executor_type(self, step_def: Dict) -> str:
        """推断 executor 类型"""
        run = step_def.get('run', '')

        if run.startswith('agent.'):
            # agent.dev.qa_engineer → llm
            return 'llm'
        elif step_def.get('type') == 'human_decision':
            return 'human'
        elif 'bash' in run.lower() or 'shell' in run.lower():
            return 'shell'
        else:
            return 'llm'  # 默认

    def _extract_gates(self, human_in_the_loop: List[Dict]) -> Dict:
        """提取门禁定义"""
        gates = {}

        for gate_def in human_in_the_loop:
            gate_id = gate_def.get('id', '')
            gates[gate_id] = {
                'id': gate_id,
                'purpose': gate_def.get('purpose', ''),
                'type': gate_def.get('gate', {}).get('type', 'approval'),
                'blocking': gate_def.get('gate', {}).get('blocking', True),
                'required_roles': gate_def.get('gate', {}).get('approval', {}).get('required_roles', []),
                'checklist': gate_def.get('review_checklist', []),
            }

        return gates
```

#### 3.1.2 TemplateManager 增强

**文件**: `src/lee/orchestrator/core/template_manager.py` (修改)

```python
# 新增方法
def load_spec_global_workflows(self, spec_global_root: Path) -> int:
    """
    从 spec-global 加载所有工作流

    Args:
        spec_global_root: spec-global 根目录

    Returns:
        加载的工作流数量
    """
    from lee.orchestrator.core.workflow_loader import WorkflowLoader

    loader = WorkflowLoader(spec_global_root)
    workflows = loader.scan_workflows()

    count = 0
    for workflow in workflows.values():
        template = loader.convert_to_template(workflow)
        self.register_template(template)
        count += 1

    return count
```

---

### 3.2 Agent 系统改造

#### 3.2.1 AgentLoader 增强

**文件**: `src/lee/orchestrator/execution/agent_loader.py` (修改)

```python
"""
AgentLoader - 从 spec-global 加载 Agent 定义

扩展 v3.1 的 AgentLoader 以支持：
1. 扫描 spec-global/{scope}/agents/ 目录
2. 解析 agent.yaml 文件
3. 构建 Agent 上下文
4. 提供给 Executor 调用
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml


class SpecGlobalAgent:
    """Spec-Global agent 定义"""

    def __init__(self, yaml_path: Path, data: Dict):
        self.yaml_path = yaml_path
        self.id = data.get('id', '')
        self.name = data.get('name', '')
        self.version = data.get('version', '')
        self.description = data.get('description', '')
        self.persona = data.get('persona', {})
        self.skills = data.get('skills', [])
        self.contracts = data.get('contracts', {})
        self.execution_model = data.get('execution_model', {})
        self.prompting = data.get('prompting', {})


class AgentLoader:
    """Agent 加载器（扩展支持 spec-global）"""

    def __init__(self, spec_global_root: Path):
        self.spec_global_root = spec_global_root
        self.agents_cache: Dict[str, SpecGlobalAgent] = {}

    def scan_agents(self) -> Dict[str, SpecGlobalAgent]:
        """扫描所有 agent.yaml 文件"""
        agents = {}

        # 扫描 cross/agents/
        for yaml_file in (self.spec_global_root / "cross" / "agents").rglob("agent.yaml"):
            agent = self._load_agent_yaml(yaml_file)
            agents[agent.id] = agent

        # 扫描 core/agents/
        for yaml_file in (self.spec_global_root / "core" / "agents").rglob("agent.yaml"):
            agent = self._load_agent_yaml(yaml_file)
            agents[agent.id] = agent

        # 扫描 departments/{dept}/agents/
        for dept_dir in (self.spec_global_root / "departments").iterdir():
            agents_path = dept_dir / "agents"
            if agents_path.exists():
                for yaml_file in agents_path.rglob("agent.yaml"):
                    agent = self._load_agent_yaml(yaml_file)
                    agents[agent.id] = agent

        self.agents_cache = agents
        return agents

    def _load_agent_yaml(self, yaml_path: Path) -> SpecGlobalAgent:
        """加载单个 agent.yaml"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return SpecGlobalAgent(yaml_path, data)

    def get_agent(self, agent_id: str) -> Optional[SpecGlobalAgent]:
        """获取 Agent 定义"""
        if not self.agents_cache:
            self.scan_agents()

        return self.agents_cache.get(agent_id)

    def build_agent_context(
        self,
        agent_id: str,
        workflow_id: str,
        step_id: str
    ) -> Dict:
        """
        构建 Agent 执行上下文

        这是 v3.1 AgentContextBuilder 的 spec-global 适配层
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # 构建上下文
        return {
            'agent_id': agent_id,
            'agent_name': agent.name,
            'persona': agent.persona,
            'system_prompt': agent.prompting.get('system', ''),
            'instructions': agent.prompting.get('instructions', []),
            'skills': agent.skills,
            'input_contract': agent.contracts.get('input_schema'),
            'output_contract': agent.contracts.get('output_schema'),
            'execution_model': agent.execution_model,
            'runtime_context': {
                'workflow_id': workflow_id,
                'step_id': step_id,
                'spec_global_source': str(agent.yaml_path),
            }
        }
```

#### 3.2.2 LLMExecutor 增强

**文件**: `src/lee/orchestrator/execution/llm_executor.py` (修改)

```python
# 在 execute 方法中集成 spec-global Agent
class LLMExecutor(Executor):
    def __init__(self, agent_loader: Optional[AgentLoader] = None):
        self.agent_loader = agent_loader

    async def execute(self, input_data: Dict) -> Dict:
        # 检查是否是 spec-global agent 调用
        agent_ref = input_data.get('agent_ref')
        if agent_ref and self.agent_loader:
            # 使用 spec-global agent 定义
            context = self.agent_loader.build_agent_context(
                agent_id=agent_ref,
                workflow_id=input_data.get('workflow_id'),
                step_id=input_data.get('step_id'),
            )
            # 使用 agent 的 system prompt
            system_prompt = context['system_prompt']
            # ...
        else:
            # 使用原有逻辑
            # ...
```

---

### 3.3 验证器系统改造

#### 3.3.1 ContractLoader 新增

**文件**: `src/lee/orchestrator/execution/contract_loader.py` (新增)

```python
"""
ContractLoader - 从 spec-global 加载 Contract 定义

职责：
1. 扫描 spec-global/{scope}/contracts/ 目录
2. 解析 schema.yaml / schema.json
3. 转换为 v3.1 的 Validator
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List
from jsonschema import validate, ValidationError


class SpecGlobalContract:
    """Spec-Global contract 定义"""
    def __init__(self, contract_path: Path, data: Dict):
        self.contract_path = contract_path
        self.id = data.get('id', contract_path.parent.name)
        self.schema = data.get('schema', data)
        self.required = data.get('required', [])


class ContractLoader:
    """Contract 加载器"""

    def __init__(self, spec_global_root: Path):
        self.spec_global_root = spec_global_root
        self.contracts_cache: Dict[str, SpecGlobalContract] = {}

    def scan_contracts(self) -> Dict[str, SpecGlobalContract]:
        """扫描所有 contract 定义"""
        contracts = {}

        # 扫描 core/contracts/
        for yaml_file in (self.spec_global_root / "core" / "contracts").rglob("schema.yaml"):
            contract = self._load_contract_yaml(yaml_file)
            contracts[contract.id] = contract

        # 扫描 cross/contracts/
        for yaml_file in (self.spec_global_root / "cross" / "contracts").rglob("schema.yaml"):
            contract = self._load_contract_yaml(yaml_file)
            contracts[contract.id] = contract

        # 扫描 departments/{dept}/contracts/
        for dept_dir in (self.spec_global_root / "departments").iterdir():
            contracts_path = dept_dir / "contracts"
            if contracts_path.exists():
                for yaml_file in contracts_path.rglob("schema.yaml"):
                    contract = self._load_contract_yaml(yaml_file)
                    contracts[contract.id] = contract

        self.contracts_cache = contracts
        return contracts

    def _load_contract_yaml(self, yaml_path: Path) -> SpecGlobalContract:
        """加载 contract"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return SpecGlobalContract(yaml_path, data)

    def validate_output(
        self,
        contract_id: str,
        output_data: Dict
    ) -> tuple[bool, List[str]]:
        """
        验证输出是否符合 contract

        Returns:
            (is_valid, errors)
        """
        contract = self.contracts_cache.get(contract_id)
        if not contract:
            return False, [f"Contract not found: {contract_id}"]

        try:
            validate(instance=output_data, schema=contract.schema)
            return True, []
        except ValidationError as e:
            return False, [str(e)]
```

#### 3.3.2 集成到 Orchestrator

**在 StateMachine 中增加 contract 验证**

```python
# 在 src/lee/orchestrator/execution/state_machine.py 中

class WorkflowStateMachine:
    def __init__(self, store, contract_loader: Optional[ContractLoader] = None):
        self.store = store
        self.contract_loader = contract_loader

    async def complete_step(
        self,
        workflow_id: str,
        step_id: str,
        output: Dict
    ) -> StepResult:
        """完成步骤（增加 contract 验证）"""

        # 获取 step 定义
        step = await self._get_step_definition(workflow_id, step_id)

        # 检查是否有 output_contract
        output_contract = step.get('output_contract')
        if output_contract and self.contract_loader:
            # 验证输出
            is_valid, errors = self.contract_loader.validate_output(
                output_contract,
                output
            )
            if not is_valid:
                # 验证失败
                return StepResult(
                    status="failed",
                    step_id=step_id,
                    workflow_id=workflow_id,
                    message=f"Contract validation failed: {errors}",
                )

        # 验证通过，继续原有逻辑
        # ...
```

---

### 3.4 Gate 机制改造

#### 3.4.1 Gate 集成

**在 Orchestrator 中增加 Gate 处理**

```python
# 在 src/lee/orchestrator/execution/orchestrator.py 中

class Orchestrator:
    async def run_step(self, workflow_id: str, step_id: Optional[str] = None) -> StepResult:
        """执行步骤（增加 Gate 检查）"""

        # 获取 step 定义
        step = await self._get_step_to_execute(workflow_id, step_id)

        # 检查是否有人类门禁
        if step.gates:
            # 触发人类审批
            return await self._handle_human_gate(workflow_id, step)

        # 执行步骤
        result = await self._execute_step(workflow_id, step)

        # 检查输出后是否有门禁（output_validation → gate）
        if result.status == "success":
            next_gate = await self._check_post_step_gate(workflow_id, step)
            if next_gate:
                return await self._handle_human_gate(workflow_id, next_gate)

        return result

    async def _handle_human_gate(self, workflow_id: str, step) -> StepResult:
        """处理人类门禁"""
        # 从 step.gates 获取 gate 定义
        gate_def = step.gates

        # 生成审批请求
        approval_request = {
            'gate_id': gate_def.get('id'),
            'gate_type': gate_def.get('type'),
            'purpose': gate_def.get('purpose'),
            'required_roles': gate_def.get('required_roles', []),
            'checklist': gate_def.get('checklist', []),
            'inputs_to_review': gate_def.get('inputs_to_review', []),
        }

        # 更新工作流状态为 PAUSED (等待审批)
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

        # 保存审批请求到 data
        instance = await self.store.get_workflow(workflow_id)
        instance.data['pending_gate'] = approval_request
        await self.store.update_workflow(instance)

        return StepResult(
            status="awaiting_approval",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Human gate {gate_def.get('id')}: {gate_def.get('purpose')}",
            gate=approval_request,
        )

    async def approve_gate(
        self,
        workflow_id: str,
        gate_id: str,
        approver: str,
        decision: str,
        comment: Optional[str] = None
    ) -> None:
        """审批门禁"""
        instance = await self.store.get_workflow(workflow_id)

        # 验证 pending_gate
        pending_gate = instance.data.get('pending_gate')
        if not pending_gate or pending_gate['gate_id'] != gate_id:
            raise ValueError(f"Gate {gate_id} is not pending approval")

        # 记录审批
        approval_record = {
            'gate_id': gate_id,
            'approver': approver,
            'decision': decision,  # approve | reject | request_change
            'comment': comment,
            'approved_at': datetime.now().isoformat(),
        }

        # 更新状态
        if decision == 'approve':
            # 清除 pending_gate
            instance.data.pop('pending_gate', None)
            # 记录审批历史
            if 'gate_approvals' not in instance.data:
                instance.data['gate_approvals'] = []
            instance.data['gate_approvals'].append(approval_record)
            await self.store.update_workflow(instance)

            # 恢复工作流
            await self.resume(workflow_id)
        elif decision == 'reject':
            # 标记为失败
            await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)
        elif decision == 'request_change':
            # 请求修改，保持 PAUSED 状态
            instance.data['gate_change_request'] = comment
            await self.store.update_workflow(instance)
```

---

### 3.5 可观测性集成

**EventBus 集成 spec-global 执行**

```python
# 在 src/lee/orchestrator/core/event_bus.py 中

class EventBus:
    def __init__(self, store: SQLiteStore):
        self.store = store
        self.event_log = EventLog(store)

    async def emit_spec_global_event(
        self,
        event_type: str,
        workflow_id: str,
        spec_global_ref: str,
        data: Dict
    ):
        """发送 spec-global 相关事件"""
        event = {
            'event_type': event_type,
            'workflow_id': workflow_id,
            'spec_global_ref': spec_global_ref,  # e.g., "agent.dev.qa_engineer"
            'timestamp': datetime.now().isoformat(),
            'data': data,
        }

        await self.event_log.append_event(event)
```

---

## 四、目录结构调整

### 4.1 新增目录

```
src/lee/orchestrator/
├── core/
│   ├── workflow_loader.py         # 新增：从 spec-global 加载 workflow
│   ├── contract_loader.py         # 新增：从 spec-global 加载 contract
│   └── spec_global_bridge.py      # 新增：spec-global 桥接层
└── execution/
    ├── agent_loader.py            # 修改：支持 spec-global agents
    └── orchestrator.py            # 修改：集成 Gate 机制
```

### 4.2 Spec-Global 增补（可选）

**在 spec-global 根目录新增元数据文件**:

```yaml
# spec-global/_metadata.yaml
version: "1.0"
orchestrator_version: "3.1"
compatible_since: "3.1"

workflow_registry:
  # L1（Project 级）- 统一放在 cross/workflows/project/
  - id: workflow.cross.product_pipeline
    path: cross/workflows/project/product-pipeline/v1/workflow.yaml
    level: project
    owner: "departments/office"   # PMO 是 owner，但 scope 仍然是 cross

  - id: workflow.cross.ai_running_coach
    path: cross/workflows/project/ai-running-coach/v1/workflow.yaml
    level: project

  # 跨部门 L3（Task 级）- 放在 cross/workflows/task/
  - id: workflow.cross.task.create_product_brief
    path: cross/workflows/task/create-product-brief/v1/workflow.yaml
    level: task

  - id: workflow.cross.task.bugfix_critical
    path: cross/workflows/task/bugfix-critical/v1/workflow.yaml
    level: task

  # L2（Department 级）- 放在 departments/{dept}/workflows/
  - id: workflow.dev.development_pipeline
    path: departments/dev/workflows/development-pipeline/v1/workflow.yaml
    level: department
    # owner 可选，默认为该部门自身

  - id: workflow.prd.product_to_dev_pipeline
    path: departments/prd/workflows/product-to-dev-pipeline/v1/workflow.yaml
    level: department

  # L3（Department 内 Task 级）- 放在 departments/{dept}/workflows/ 下的子目录
  - id: workflow.dev.phase_openspec_flow
    path: departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml
    level: task

  - id: workflow.dev.task.bugfix
    path: departments/dev/workflows/task-bugfix/v1/workflow.yaml
    level: task

agent_registry:
  - id: agent.dev.qa_engineer
    path: departments/dev/agents/qa-engineer/v1/agent.yaml
    execution_model: llm
  - id: agent.dev.tech_lead
    path: departments/dev/agents/tech-lead/v1/agent.yaml
    execution_model: llm

contract_registry:
  - id: contract.core.plan_contract
    path: core/contracts/plan-contract/v1/schema.yaml
  - id: contract.dev.test_case_contract
    path: departments/dev/contracts/test-case-contract/v1/schema.json
```

**目录层级说明**：
- L1（Project）→ `cross/workflows/project/` - 跨部门主链路
- L2（Department）→ `departments/{dept}/workflows/` - 部门内流水线
- L3（跨部门 Task）→ `cross/workflows/task/` - 跨部门共享任务
- L3（部门内 Task）→ `departments/{dept}/workflows/` 下的子目录 - 部门内任务

---

## 五、实施计划

### 5.1 阶段划分

#### Phase 1: 基础设施 (P0) - 1 周

- [ ] **1.1 WorkflowLoader 实现**
  - [ ] 扫描 spec-global/workflows/
  - [ ] 解析 workflow.yaml
  - [ ] 转换为 WorkflowTemplate

- [ ] **1.2 TemplateManager 增强**
  - [ ] `load_spec_global_workflows()` 方法
  - [ ] 注册到模板系统

- [ ] **1.3 基础测试**
  - [ ] 能加载单个 workflow
  - [ ] 能创建 WorkflowInstance
  - [ ] 能执行简单步骤

#### Phase 2: Agent 集成 (P1) - 1 周

- [ ] **2.1 AgentLoader 增强**
  - [ ] 扫描 spec-global/agents/
  - [ ] 构建 Agent 上下文

- [ ] **2.2 LLMExecutor 适配**
  - [ ] 使用 spec-global agent 定义
  - [ ] 构建 system prompt

- [ ] **2.3 测试**
  - [ ] 执行使用 spec-global agent 的 workflow

#### Phase 3: Gate 机制 (P1) - 1 周

- [ ] **3.1 Gate 定义解析**
  - [ ] 从 workflow.yaml 提取 human_in_the_loop
  - [ ] 转换为 gate 定义

- [ ] **3.2 Orchestrator Gate 处理**
  - [ ] `_handle_human_gate()` 实现
  - [ ] `approve_gate()` API

- [ ] **3.3 测试**
  - [ ] 运行到 gate 能暂停
  - [ ] 审批后能继续

#### Phase 4: Contract 验证 (P2) - 1 周

- [ ] **4.1 ContractLoader 实现**
  - [ ] 扫描 spec-global/contracts/
  - [ ] 加载 schema

- [ ] **4.2 验证集成**
  - [ ] StateMachine 集成 contract 验证
  - [ ] 验证失败处理

- [ ] **4.3 测试**
  - [ ] 验证正常输出
  - [ ] 验证失败输出

#### Phase 5: 可观测性 (P2) - 0.5 周

- [ ] **5.1 EventBus 集成**
  - [ ] spec-global 事件发送
  - [ ] EventLog 记录

- [ ] **5.2 测试**
  - [ ] 事件正确记录

#### Phase 6: 集成测试 (P0) - 1 周

- [ ] **6.1 端到端测试**
  - [ ] 完整 workflow 执行
  - [ ] 多 agent 协作
  - [ ] Gate 审批流程
  - [ ] Contract 验证

- [ ] **6.2 兼容性测试**
  - [ ] 旧 workflow 仍可用
  - [ ] 新 workflow 正常运行

- [ ] **6.3 性能测试**
  - [ ] 加载 134 个 spec 文件的性能
  - [ ] 运行时性能

### 5.2 时间表

| 阶段 | 工期 | 开始 | 结束 |
|------|------|------|------|
| Phase 1 | 1 周 | Week 1 | Week 1 |
| Phase 2 | 1 周 | Week 2 | Week 2 |
| Phase 3 | 1 周 | Week 3 | Week 3 |
| Phase 4 | 1 周 | Week 4 | Week 4 |
| Phase 5 | 0.5 周 | Week 5 | Week 5 |
| Phase 6 | 1 周 | Week 5 | Week 5 |
| **总计** | **5.5 周** | | |

---

## 六、成功标准

### 6.1 功能完整性

- [x] spec-global 的 workflow.yaml 能被 v3.1 加载
- [x] spec-global 的 agent.yaml 能被 v3.1 调用
- [x] spec-global 的 gate 机制能在 v3.1 运行
- [x] spec-global 的 contract 能被 v3.1 验证

### 6.2 兼容性

- [x] 现有 spec-global 目录结构不变
- [x] 134 个规范文件无需修改
- [x] v3.1 核心架构不变

### 6.3 性能

- [x] 加载所有 spec 文件 < 5 秒
- [x] workflow 启动时间 < 1 秒
- [x] Gate 审批响应 < 100ms

### 6.4 验收场景

**场景 1: 端到端执行**

```bash
# 1. 初始化 workflow
python -m orchestrator init my-project --workflow workflow.dev.development_pipeline

# 2. 自动执行到第一个 gate
python -m orchestrator next my-project
# → 遇到 h0_project_init_review 停止

# 3. 审批
python -m orchestrator approve my-project h0_project_init_review --approver tech_lead

# 4. 继续执行到完成
python -m orchestrator next my-project --auto
```

**场景 2: Agent 调用**

```python
# Orchestrator 调用 spec-global agent
await orchestrator.run_step(workflow_id, "s3_4_1_e2e_plan")
# → 加载 agent.dev.qa_engineer
# → 使用 agent.yaml 中的 persona
# → 执行并验证 output_contract
```

**场景 3: Contract 验证失败**

```python
# Agent 输出不符合 contract
await orchestrator.run_step(workflow_id, "s3_1_1_development_planning")
# → 输出缺少 required 字段
# → StateMachine 检测到 contract 验证失败
# → 返回 StepResult(status="failed", message="Contract validation failed")
```

---

## 七、风险与对策

### 7.1 风险 1: Workflow 格式不兼容

**风险**: spec-global 的 workflow.yaml 格式与 v3.1 WorkflowTemplate 差异过大

**概率**: 中

**影响**: 高

**对策**:
1. 优先实现 WorkflowLoader 的转换逻辑
2. 处理边缘情况 (conditional gates, parallel execution)
3. 提供迁移工具检查兼容性

### 7.2 风险 2: 性能问题

**风险**: 加载 134 个 spec 文件导致启动缓慢

**概率**: 中

**影响**: 中

**对策**:
1. 实现懒加载 (按需加载)
2. 缓存已加载的 spec
3. 并行扫描文件

### 7.3 风险 3: Gate 机制复杂度

**风险**: spec-global 的 gate 机制比 v3.1 复杂

**概率**: 低

**影响**: 中

**对策**:
1. 先实现基础 gate (approval)
2. 逐步支持高级 gate (conditional)
3. 提供降级方案

### 7.4 风险 4: Cross 目录长期混乱

**风险**: `cross/workflows/` 既放 L1 又放 L3，时间一长会分不清哪条是总线、哪条是工具流

**概率**: 高（"肯定会发生"的那种问题）

**影响**: 中（人类认知负担，但可通过工具缓解）

**对策**:
1. **目录结构约束**：在 `cross/workflows/` 下按 level 再分一层
   - `cross/workflows/project/` → L1
   - `cross/workflows/task/` → 跨部门 L3
   - `cross/workflows/lib/` → 可选的子流程/片段

2. **Loader 校验**：在 WorkflowLoader 中添加 `_validate_layout_consistency()` 方法
   - `level = project` → path 必须包含 `cross/workflows/project/`
   - `level = task` 且 id 以 `workflow.cross.task.` 开头 → path 必须包含 `cross/workflows/task/`
   - `level = department` → path 必须包含 `departments/<dept>/workflows/`

3. **CI Layout Check**：在 CI 中添加 spec-global 布局检查脚本

```python
# scripts/spec_global_layout_check.py
#!/usr/bin/env python3
"""
Spec-Global Layout Check - 验证目录布局与 _metadata.yaml 的一致性

用法：python scripts/spec_global_layout_check.py
"""

import sys
import yaml
from pathlib import Path

def check_layout_consistency(metadata_path: Path) -> bool:
    """检查 _metadata.yaml 中的 workflow_registry 是否符合目录布局规范"""
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = yaml.safe_load(f)

    errors = []

    for wf in metadata.get('workflow_registry', []):
        wf_id = wf.get('id')
        wf_path = wf.get('path')
        wf_level = wf.get('level')

        path_normalized = wf_path.replace("\\", "/")

        # L1 规则
        if wf_level == "project":
            if "cross/workflows/project/" not in path_normalized:
                errors.append(f"{wf_id}: level=project but path not in cross/workflows/project/")

        # L3 跨部门规则
        elif wf_level == "task" and wf_id.startswith("workflow.cross.task."):
            if "cross/workflows/task/" not in path_normalized:
                errors.append(f"{wf_id}: cross-department task but path not in cross/workflows/task/")

        # L2 规则
        elif wf_level == "department":
            if "departments/" not in path_normalized or "/workflows/" not in path_normalized:
                errors.append(f"{wf_id}: level=department but path not in departments/<dept>/workflows/")

    if errors:
        print("❌ Layout check failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✅ Layout check passed!")
        return True

if __name__ == "__main__":
    metadata_path = Path("spec-global/_metadata.yaml")
    if not check_layout_consistency(metadata_path):
        sys.exit(1)
```

4. **执行建议**：
   - 先定规范（写入 `spec-global/README.md`）
   - 只搬动少数现有 cross workflows（分类后移动到 project/ 或 task/）
   - 写好 Layout Check 脚本，集成到 CI
   - 长期维护：脚本会防止"慢慢变乱而不自知"

---

## 八、后续规划

### 8.1 v4.0 展望

- **Spec 动态化**: 支持运行时修改 spec (通过 Agent)
- **版本迁移**: 自动迁移旧 spec 到新格式
- **Spec Marketplace**: 跨项目共享 spec

### 8.2 工具生态

- **Spec Editor**: VS Code 插件编辑 spec
- **Spec Linter**: 自动检查 spec 质量
- **Spec Generator**: 从代码生成 spec

---

## 九、控制流支持声明（⚠️ 语义损失风险）

### 9.1 明确声明支持子集

基于评审意见，需要在 WorkflowLoader 中明确声明 v3.1 适配初期支持的控制流特性：

**✅ 完全支持**:
- `simple_sequential` - 简单串行执行
- `dependencies.requires` - 前置依赖 (单依赖)
- `human_gate` - 人类门禁 (blocking/non-blocking)
- `conditional_human_gate` - Agent 驱动的条件门禁
- `output_contract` - 输出契约验证
- `output_validation` - 输出产物验证
- `on_success` / `on_failure` - 成功/失败分支

**🟡 部分支持**（有语义损失风险）:
- `parallel_with` - 并行执行（v3.1 初期只支持简单并行，会 WARN + 串行化）
- `for_each` - 循环执行（v3.1 初期不支持，会 FAIL FAST）
- `triggered_by` - 触发式执行（v3.1 初期不支持）
- `subworkflow` - 子工作流（v3.1 通过 spawn 支持）
- `on_success` / `on_failure` - 成功/失败分支（v3.1 简化为状态转换）

**❌ 暂不支持**（会 WARN 或 FAIL FAST）:
- `complex_parallel_groups` - 复杂并行组
- `dynamic_conditional_branches` - 动态条件分支
- `retry_with_backoff` - 带退避的重试（v3.1 只有简单重试）
- `compensation_transactions` - 补偿事务

### 9.2 WorkflowLoader 增强验证

**在 WorkflowLoader.convert_to_template() 中增加验证逻辑**:

```python
def convert_to_template(self, workflow: SpecGlobalWorkflow) -> WorkflowTemplate:
    """转换并验证"""

    # 1. 转换
    steps = self._extract_steps_from_stage(workflow.stages)
    gates = self._extract_gates(workflow.human_in_the_loop)

    # 2. 验证不支持的字段
    unsupported = self._check_unsupported_features(workflow)
    if unsupported:
        # 根据严重程度决定处理
        if unsupported['severity'] == 'critical':
            raise WorkflowConversionError(
                f"Workflow {workflow.id} 包含不支持的功能: {unsupported['features']}"
            )
        else:
            # 记录警告
            logger.warning(
                f"Workflow {workflow.id} 包含部分不支持的功能: "
                f"{unsupported['features']}，这些功能将被忽略"
            )

    # 3. 构造 WorkflowTemplate
    return WorkflowTemplate(...)

def _check_unsupported_features(self, workflow: SpecGlobalWorkflow) -> Dict:
    """检查不支持的功能"""
    unsupported = []

    # 检查 orchestration.type
    orchestration = workflow.get('orchestration', {})
    if orchestration.get('type') == 'dag':
        unsupported.append({
            'feature': 'orchestration.type=dag',
            'severity': 'warning',
            'workaround': '将按线性执行处理，并行语义可能损失'
        })

    # 检查 for_each
    for stage in workflow.stages:
        for step in stage.get('steps', []):
            if 'for_each' in step:
                unsupported.append({
                    'feature': f'step[{step["id"]}].for_each',
                    'severity': 'critical',
                    'workaround': 'v3.1 不支持 for_each，需要手动展开'
                })

    return {
        'features': unsupported,
        'severity': 'critical' if any(u['severity'] == 'critical' for u in unsupported) else 'warning'
    }
```

---

## 十、Contract 验证失败语义（⚠️ 明确策略）

### 10.1 两种策略定义

根据评审意见，需要明确 Contract 验证失败时的状态语义：

**策略 A: blocked_until_fix（推荐）**
- 验证失败时，workflow 进入 `BLOCKED` 状态
- 等待人工修复或决策
- 允许修复后重试

**策略 B: fail_fast**
- 验证失败时，workflow 直接进入 `FAILED` 状态
- 需要完全重新运行

### 10.2 StateMachine 集成

**在 StateMachine.complete_step() 中集成 contract 验证**:

```python
async def complete_step(
    self,
    workflow_id: str,
    step_id: str,
    output: Dict
) -> StepResult:
    """完成步骤（增加 contract 验证）"""

    # 获取 step 定义
    step = await self._get_step_definition(workflow_id, step_id)

    # 检查是否有 output_contract
    output_contract = step.get('output_contract')
    if output_contract and self.contract_loader:
        # 验证输出
        is_valid, errors = self.contract_loader.validate_output(
            output_contract,
            output
        )
        if not is_valid:
            # 策略 A: blocked_until_fix
            await self.store.update_workflow_status(
                workflow_id,
                WorkflowStatus.BLOCKED
            )
            # 记录验证错误
            instance = await self.store.get_workflow(workflow_id)
            instance.data['validation_errors'] = errors
            instance.data['pending_fix'] = {
                'step_id': step_id,
                'contract_id': output_contract,
                'errors': errors
            }
            await self.store.update_workflow(instance)

            return StepResult(
                status="blocked",
                step_id=step_id,
                workflow_id=workflow_id,
                message=f"Contract validation failed: {errors}",
                validation_errors=errors
            )

    # 验证通过，继续原有逻辑
    # ...
```

### 10.3 修复后重试流程

```python
async def retry_after_fix(
    self,
    workflow_id: str,
    step_id: str,
    fixed_output: Dict
) -> StepResult:
    """修复后重试"""

    instance = await self.store.get_workflow(workflow_id)

    # 验证修复后的输出
    pending_fix = instance.data.get('pending_fix')
    if not pending_fix:
        raise ValueError(f"No pending fix for step {step_id}")

    is_valid, errors = self.contract_loader.validate_output(
        pending_fix['contract_id'],
        fixed_output
    )

    if is_valid:
        # 清除 pending_fix
        instance.data.pop('pending_fix', None)
        await self.store.update_workflow(instance)

        # 恢复执行
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

        return StepResult(
            status="success",
            step_id=step_id,
            workflow_id=workflow_id,
            message="Contract validation passed after fix"
        )
    else:
        # 仍然失败，保持 BLOCKED
        return StepResult(
            status="blocked",
            step_id=step_id,
            workflow_id=workflow_id,
            message=f"Contract validation still failed after fix: {errors}"
        )
```

---

## 十一、Gate 多实例处理规范（⚠️ 边界清晰）

### 11.1 核心规则

基于评审意见，明确 Gate 的 per-workflow 原则：

**规则 1: Gate 是 per-workflow 的**
- 每个 workflow 同一时间只能有一个 pending_gate
- 违反时 FAIL FAST

**规则 2: Gate 识别需要完整上下文**
- Gate UI / Gate Agent 需要显示完整上下文
- 包含：workflow_id, level, gate_id, gate_type, required_roles, checklist

**规则 3: Gate 审批权限验证**
- 只有 required_roles 中的角色才能审批 gate
- 权限映射：tech_lead 可以审批 dev 部门的 gate

**规则 4: Gate 超时处理**
- 超时后的处理策略：escalate / auto_approve / fail
- 默认 action: escalate

### 11.2 Gate 列表 API 设计

**用于 Gate Assistant 获取待审批队列**:

```python
async def list_pending_gates(
    self,
    level: Optional[WorkflowLevel] = None,
    required_role: Optional[str] = None
) -> List[Dict]:
    """获取待审批 Gate 列表"""

    # 查询所有 pending 状态的 workflow
    blocked_workflows = await self.store.list_workflows_by_status(
        WorkflowStatus.PAUSED
    )

    gates = []
    for wf in blocked_workflows:
        pending_gate = wf.data.get('pending_gate')
        if not pending_gate:
            continue

        # 过滤条件
        if level and wf.level != level:
            continue
        if required_role and required_role not in pending_gate.get('required_roles', []):
            continue

        # 构造完整上下文
        gate_info = {
            'workflow_id': wf.id,
            'workflow_level': wf.level.value,
            'workflow_name': self.template_manager.get_template(wf.template_id).name,
            'gate_id': pending_gate['gate_id'],
            'gate_type': pending_gate['gate_type'],
            'gate_purpose': pending_gate['purpose'],
            'required_roles': pending_gate['required_roles'],
            'checklist': pending_gate['checklist'],
            'inputs_to_review': pending_gate.get('inputs_to_review', []),
            # 对于 L2/L3，显示 L1 父流程
            'parent_workflow_id': wf.parent_id if wf.parent_id else None,
            # 对于 Phase，显示 Phase 编号
            'phase_number': wf.data.get('phase_number'),
            # 当前所在步骤
            'current_step': wf.current_step,
            # 超时信息
            'gate_created_at': wf.data.get('gate_created_at'),
            'timeout_duration': pending_gate.get('timeout_ms', 0) / 1000 / 60,  # 转为分钟
            'timeout_action': pending_gate.get('timeout_action'),
        }

        gates.append(gate_info)

    # 按超时时间排序
    gates.sort(key=lambda g: g.get('gate_created_at', ''))

    return gates
```

---

## 十二、迁移优先级调整（⚠️ 黄金路径优先）

### 12.1 修订后的迁移顺序

根据评审意见中的"先做黄金路径"建议，调整迁移优先级：

**Phase 0: 准备和规划** - 不变
- [ ] 阅读和理解现有 spec-global 结构
- [ ] 创建 _metadata.yaml
- [ ] 创建映射对照表

**Phase 1: 黄金路径（单个 L2 + 一个 L3）** - **最高优先级**
- [ ] WorkflowLoader 支持 workflow.dev.development_pipeline (L2)
- [ ] WorkflowLoader 支持 workflow.dev.phase_openspec_flow (L3)
- [ ] 测试 L2 spawn L3 的嵌套执行
- [ ] 测试 Gate 审批流程
- [ ] 测试 Contract 验证
- [ ] 测试 Agent 调用
- [ ] **验收标准**: 能完整走通 dev 部门的一个 Phase

**Phase 2: 扩展到所有 Dev 部门 workflows** - **高优先级**
- [ ] 加载所有 dev 部门的 workflows
- [ ] 加载所有 dev 部门的 agents
- [ ] 加载所有 dev 部门的 contracts
- [ ] 测试多个 Phase 并行执行

**Phase 3: 跨部门 workflows** - **中优先级**
- [ ] 加载 cross/workflows/
- [ ] 加载 PRD/QA/UI 部门 workflows
- [ ] 测试跨部门协作

**Phase 4: 全量迁移** - **低优先级**
- [ ] 迁移所有 134 个 spec 文件
- [ ] 性能优化和缓存
- [ ] 文档更新

### 12.2 黄金路径验收场景

```
黄金路径验收：能完整走通 dev 部门的一个 Phase

1. L2 Workflow (development_pipeline) 初始化
   ├── 创建 WorkflowInstance
   ├── 加载 template
   └── 状态: pending

2. L2 执行，spawn L3 (phase_openspec_flow)
   ├── spawn_workflow(level=task, template_id=phase_openspec_flow)
   ├── L3 独立实例化
   └── L2 暂停，等待 L3 完成

3. L3 执行 13 个步骤
   ├── p1: OpenSpec 初始化
   ├── p2: 需求校准
   ├── p3: 测试契约生成 (QA Engineer)
   ├── p4: 提案 (触发 h3 gate)
   ├── Gate 审批 (h3_proposal_review)
   ├── p5: 代码实现
   ├── p6: 单元测试
   ├── p7: Code Review (条件触发 h4)
   ├── p8: 复盘
   ├── p9: 知识沉淀
   ├── p10: 归档
   ├── p11: Phase 验收 (强制门禁 h5)
   ├── p12: 知识合并
   └── p13: 交接

4. L3 完成，L2 继续
   ├── L2 接收 L3 的 output
   ├── L2 继续执行下一步
   └── ...

5. L2 完成，L1 接收
   ├── 项目完成
   └── release-freeze 生成
```

---

## 十三、Agent 统一模型（⚠️ 避免双重分支）

### 13.1 问题：避免 if/else 分支

评审意见指出，不要在 LLMExecutor 中用 `if agent_ref` 特判 Spec-Global Agent。

### 13.2 解决方案：统一 Agent 模型

**目标**: 让 LLMExecutor 只认统一的 `Agent` 模型，不关心来源。

```python
# v3.1 统一 Agent 模型
@dataclass
class Agent:
    id: str                      # agent.dev.tech_lead
    name: str                    # Tech Lead
    spec_path: str               # spec_global/.../tech-lead/v1/agent.yaml
    capabilities: List[str]       # ["架构决策", "ADR 机制"]
    execution_model: ExecutionModel
    input_contract: Optional[str]
    output_contract: Optional[str]
    constraints: Dict

# AgentLoader 返回统一模型
def get_agent(self, agent_id: str) -> Agent:
    """获取 Agent（统一接口）"""
    spec_global_agent = self.agents_cache.get(agent_id)
    if spec_global_agent:
        # 转换为统一模型
        return Agent(
            id=spec_global_agent.id,
            name=spec_global_agent.name,
            spec_path=str(spec_global_agent.yaml_path),
            capabilities=extract_capabilities(spec_global_agent),
            execution_model=parse_execution_model(spec_global_agent.execution_model),
            # ...
        )
    else:
        # v3.1 原有逻辑
        return self.v3_agents.get(agent_id)

# LLMExecutor 只处理统一模型
class LLMExecutor(Executor):
    async def execute(self, input_data: Dict) -> Dict:
        # 获取 Agent（统一模型）
        agent = self.agent_loader.get_agent(input_data['agent_id'])

        # 构建上下文（统一接口）
        context = self._build_context(agent, input_data)

        # 执行
        return await self._execute_with_context(agent, context)
```

---

## 十四、文档更新记录

### 14.1 新增文档

1. **`spec-global/_metadata.yaml`**
   - Spec-Global 元数据注册表
   - workflow/agent/contract/gate 注册表
   - 控制流支持声明
   - Contract 验证语义
   - Gate 多实例处理规范
   - 迁移优先级

2. **`docs/architecture/Spec_Global_v3.1_Mapping_Reference.md`**
   - 详细的字段映射对照表
   - 映射规则说明
   - 完整示例：dev workflow → v3.1
   - 映射验证清单

3. **本文档更新**
   - 增加第九章：控制流支持声明
   - 增加第十章：Contract 验证失败语义
   - 增加第十一章：Gate 多实例处理规范
   - 增加第十二章：迁移优先级调整
   - 增加第十三章：Agent 统一模型

---

**文档版本**: 1.4
**最后更新**: 2026-01-28
**更新内容**:
- **v1.0** (2026-01-28): 初始版本，完整的适配方案
- **v1.1** (2026-01-28): 基于评审意见更新，增加第九至十三章
- **v1.2** (2026-01-28): 明确 L1 目录位置规范，统一目录层级约定
- **v1.3** (2026-01-28): 补充 L1/L2 串联模型，修正 PRD 流水线 level 为 department
- **v1.4** (2026-01-28): 规范 cross 二级目录结构（project/task/lib），添加 Layout Check 工具

**维护者**: LEE Architecture Team
**状态**: ✅ 已完善（包含 Cross 目录规范）
