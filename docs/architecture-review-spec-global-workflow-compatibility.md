# LEE 框架架构评审文档

## Orchestrator 与 spec-global 工作流格式兼容性方案评审

**文档编号**: AR-2025-001
**创建日期**: 2026-02-05
**评审状态**: 待决策
**评审人**: 架构团队

---

## 目录

1. [问题背景](#1-问题背景)
2. [平台能力缺口报告](#2-平台能力缺口报告)
3. [原方案概述](#3-原方案概述)
4. [详细差异分析](#4-详细差异分析)
5. [架构评审意见](#5-架构评审意见)
6. [替代方案设计](#6-替代方案设计)
7. [最终建议](#7-最终建议)
8. [决策检查清单](#8-决策检查清单)

---

## 1. 问题背景

### 1.1 问题描述

LEE 框架的 `Orchestrator` 无法解析和执行 `spec-global` 目录下的测试用例设计工作流 (`workflow.qa.test_case_design_pipeline`)。工作流一直处于 `blocked` 状态，QA 部门无法通过 Orchestrator 执行测试用例设计流程。

### 1.2 根本原因

LEE 框架存在两套工作流定义体系，由不同团队在不同时期设计：

| 维度 | Orchestrator 原生格式 | spec-global 企业级格式 |
|------|---------------------|---------------------|
| **设计目标** | 简化工作流编排 | 企业级工作流管理 |
| **复杂度** | 轻量级 | 重量级 |
| **设计哲学** | 约定优于配置 | 显式声明一切 |
| **使用场景** | 内部工具链、快速开发 | 多团队协作、合规要求 |
| **存放位置** | `examples/templates.yaml` | `spec-global/departments/*/workflows/` |

### 1.3 核心矛盾

```
Orchestrator 期望: 扁平的 steps 列表
spec-global 实际: 嵌套的 stages → steps 结构
```

---

## 2. 平台能力缺口报告

### Ticket #1: Orchestrator 无法加载 spec-global 工作流格式

| 属性 | 值 |
|------|-----|
| **工作流** | qa.test_case_design_pipeline |
| **缺失能力** | TemplateManager 不支持 spec-global 工作流格式 |
| **影响** | QA 部门无法通过 Orchestrator 执行测试用例设计工作流 |
| **优先级** | P0 |

**格式差异对比**:

```yaml
# Orchestrator 期望格式
level: department
steps:
  - id: step_1
    kind: agent
    agent: agent.qa.xxx

# spec-global 格式
kind: workflow
version: 1.0
stages:  # 嵌套结构
  - id: s1_input_validation
    steps:
      - id: s1_1_validate_inputs
        run: agent.qa.requirement_alignment_agent
state_machine: {...}
contracts: {...}
gates: {...}
```

### Ticket #2: 工作流步骤数据结构不兼容

| 属性 | 值 |
|------|-----|
| **工作流** | qa.test_case_design_pipeline |
| **缺失能力** | spec-global 的 stage/step 结构与 Orchestrator 的 Step 模型不兼容 |
| **优先级** | P0 |

**结构对比**:

```yaml
# spec-global Step 结构
- id: s1_1_validate_inputs
  run: agent.qa.requirement_alignment_agent  # 引用格式
  inputs:
    - prd: "$inputs.prd"  # 数组 + 变量引用
  outputs:
    - path: "validation/report.yaml"
      include: [...]  # 嵌套结构
  gate:
    ref: gate.qa.design_input_gate  # 外部引用
    on_fail:
      action: block_and_report

# Orchestrator Step 模型
Step(
    id="s1_1_validate_inputs",
    kind="agent",
    agent_id="agent.qa.requirement_alignment_agent",
    input={"prd": {"$ref": "$inputs.prd"}},  # 对象格式
    outputs=[OutputSpec(...)],
    gate_id="design_input_gate"  # 字符串
)
```

### Ticket #3: 输入契约绑定机制缺失

| 属性 | 值 |
|------|-----|
| **工作流** | qa.test_case_design_pipeline |
| **缺失能力** | Orchestrator 无法解析和绑定工作流的输入契约 |
| **优先级** | P0 |

**契约定义**:

```yaml
contracts:
  inputs:
    - prd:
        path: "../../../prd/contracts/frozen-detailed-prd-contract/v1/schema.json"
        required: true
    - technical_architecture:
        path: "../../../dev/contracts/frozen-technical-architecture-contract/v1/schema.json"
        required: true
```

### Ticket #4: 门禁系统未集成

| 属性 | 值 |
|------|-----|
| **工作流** | qa.test_case_design_pipeline |
| **缺失能力** | Orchestrator 与 spec-global 的门禁系统未集成 |
| **优先级** | P0 |

**门禁引用**:

```yaml
gate:
  ref: gate.qa.design_input_gate  # 引用外部文件
  on_fail:
    action: block_and_report
    state: BLOCKED

# 外部门禁文件位置
gates:
  design_input_gate:
    ref: ../../gates/design-input-gate/v1/gate.yaml
```

---

## 3. 原方案概述

### 3.1 方案架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     spec-global 工作流定义                        │
│  (kind: workflow, stages, contracts, state_machine, gates)       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              SpecGlobalWorkflowAdapter (NEW)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. 格式检测：kind == "workflow"                           │  │
│  │ 2. 契约解析：提取 contracts.inputs/outputs                │  │
│  │ 3. 状态机映射：state_machine → 隐式依赖                    │  │
│  │ 4. 步骤展平：stages[].steps → 扁平 steps                  │  │
│  │ 5. 变量解析：$inputs.xxx → 运行时解析                      │  │
│  │ 6. 门禁加载：gate.ref → 外部门禁文件                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TemplateManager (增强)                         │
│  - _parse_template_doc(): 检测 kind 字段                         │
│  - _parse_spec_global_format(): 新增解析方法                    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator (增强)                          │
│  - 契约绑定：create_workflow() 支持 input_params                │
│  - 变量解析：RuntimeResolver 支持 $inputs 语法                   │
│  - 门禁集成：加载外部门禁文件                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件设计

#### SpecGlobalWorkflowAdapter

```python
class SpecGlobalWorkflowAdapter:
    """spec-global 工作流格式适配器"""

    def detect_format(self, doc: Dict[str, Any]) -> bool:
        """检测是否为 spec-global 格式"""
        return doc.get("kind") == "workflow"

    def adapt(self, doc: Dict[str, Any], template_id: str) -> Dict[str, Any]:
        """适配 spec-global 格式为 Orchestrator 格式"""
        contracts = self._extract_contracts(doc)
        steps = self._flatten_stages(doc.get("stages", []), contracts)
        state_machine = doc.get("state_machine", {})
        level = self._infer_level(doc)

        return {
            "id": doc.get("id", template_id),
            "level": level,
            "steps": steps,
            "contracts": contracts,
            "state_machine": state_machine,
            ...
        }
```

#### RuntimeResolver

```python
class RuntimeResolver:
    """运行时变量解析器"""

    def resolve(self, value: Any, context: Dict[str, Any]) -> Any:
        """
        支持：
        - $inputs.xxx: 工作流输入契约
        - $step_id.field: 步骤输出引用
        """
        if isinstance(value, str) and value.startswith("$"):
            return self._resolve_ref(value, context)
        ...
```

### 3.3 实施路线图

| 阶段 | 任务 | 工作量 | 优先级 |
|------|------|--------|--------|
| Phase 1 | 基础适配（适配器、TemplateManager增强、契约绑定） | 2周 | P0 |
| Phase 2 | 门禁集成（外部门禁加载、失败处理） | 1周 | P0 |
| Phase 3 | 高级特性（状态机、错误处理、质量指标） | 2周 | P1 |

---

## 4. 详细差异分析

### 4.1 结构映射表

| spec-global 字段 | Orchestrator 对应 | 状态 | 说明 |
|-----------------|-----------------|------|------|
| `kind: workflow` | - | ❌ 不识别 | 需要添加格式检测 |
| `id` | `id` | ✅ 兼容 | 直接映射 |
| `version` | - | ❌ 不支持 | 可忽略或存储到 config |
| `concepts` | - | ❌ 不支持 | 业务术语定义 |
| `contracts.inputs/outputs` | - | ❌ 不支持 | **关键缺口** |
| `state_machine` | 隐式依赖 | ❌ 不支持 | **关键缺口** |
| `stages` | `steps` | ❌ 需展平 | **核心问题** |
| `stages[].steps` | `steps` | ❌ 嵌套结构 | 需要展平逻辑 |
| `stages[].steps[].run` | `agent`/`skill` | ❌ 不识别 | 需解析 `agent.qa.xxx` |
| `stages[].steps[].inputs[]` | `input` | ⚠️ 部分兼容 | 数组 vs 对象 |
| `stages[].steps[].outputs[]` | `outputs[]` | ⚠️ 部分兼容 | 结构有差异 |
| `gates` | `human_gate` | ❌ 不支持 | 外部引用 vs 内联 |
| `human_in_the_loop` | - | ❌ 不支持 | **关键缺口** |
| `error_handling` | - | ❌ 不支持 | 错误策略缺失 |
| `quality_metrics` | - | ❌ 不支持 | 可观测性缺失 |
| `observability` | - | ❌ 不支持 | 监控集成缺失 |
| `dependencies` | `depends_on` | ⚠️ 部分兼容 | 语法不同 |

### 4.2 关键缺口详解

#### 缺口 1：输入契约绑定 (P0)

```yaml
# spec-global 定义
contracts:
  inputs:
    - prd:
        path: "../../../prd/contracts/frozen-detailed-prd-contract/v1/schema.json"
        required: true
```

**问题**: Orchestrator 创建工作流时无法接收和验证这些契约路径。

**影响**: 工作流无法启动，因为缺少必需的输入数据。

#### 缺口 2：状态机驱动 (P0)

```yaml
# spec-global 定义
state_machine:
  states:
    - INIT: "初始化"
    - REQUIREMENT_ALIGNMENT: "需求对齐"
  transitions:
    INIT:
      - to: REQUIREMENT_ALIGNMENT
        trigger: "workflow_started"
```

**问题**: Orchestrator 使用隐式状态转换（基于步骤依赖），无法执行显式状态机。

**影响**: 无法实现复杂的条件分支和回退逻辑。

#### 缺口 3：外部门禁引用 (P0)

```yaml
# spec-global 定义
gate:
  ref: gate.qa.design_input_gate
  on_fail:
    action: block_and_report
    state: BLOCKED

# 引用的外部文件
gates:
  design_input_gate:
    ref: ../../gates/design-input-gate/v1/gate.yaml
```

**问题**: Orchestrator 只支持内联 `human_gate`，无法加载外部门禁文件。

**影响**: 门禁逻辑无法复用，工作流无法在门禁失败时正确处理。

#### 缺口 4：变量引用语法 (P1)

```yaml
# spec-global 语法
inputs:
  - prd: "$inputs.prd"
  - features: "$s3_1_extract_features.feature_list"
```

**问题**: Orchestrator 的 `TemplateResolver` 不支持 `$inputs.xxx` 和 `$step_id.field` 语法。

**影响**: 步骤无法正确接收前置步骤的输出。

---

## 5. 架构评审意见

### 评审结论：方案存在重大缺陷，建议重新设计

**总体评级**: ⚠️ **不推荐实施 (REROUT)**

---

### 5.1 核心问题批判

#### 问题 1："假适配"陷阱 - 状态机被忽略 🔴

**方案中的处理**:
```python
# 方案只是存储 state_machine 到 config
state_machine = doc.get("state_machine", {})
return {..., "config": {..., "state_machine": state_machine}}
```

**批判**: 这不是解决方案，这是"把问题藏起来"。

spec-global 工作流的核心价值在于**显式状态机驱动的执行**:

```yaml
state_machine:
  transitions:
    TEST_CASE_REVIEW:
      - to: PLAYWRIGHT_GENERATION
        trigger: "review_approved"  # 人类决定
      - to: REVIEW_REVISION        # 回退！
        trigger: "review_rejected"
```

Orchestrator 当前的执行模型是基于**DAG 依赖驱动**，无法表达:
- 条件分支（根据上一步结果决定下一步）
- 状态回退（review rejected → 回到 revision）
- 人工干预点（等待人类审批）

**根本矛盾**: 两个系统的执行范式不同，无法通过格式转换解决。

---

#### 问题 2：步骤 ID 命名空间方案有缺陷 🟡

**方案中的处理**:
```python
full_step_id = f"{stage_id}.{step_id}"  # s1_input_validation.s1_1_validate_inputs
```

**批判**:

1. **冗余**: stage 已经是逻辑分组，`s1_1` 的前缀已经表明属于 `s1`
2. **语义混淆**: `.` 在 YAML 中可能被解释为路径分隔符
3. **破坏现有引用**: 如果 spec-global 工作流中已有跨 stage 引用（如 `depends_on: s1_1_validate_inputs`），转换后会失效
4. **不必要**: Orchestrator 的 Step 模型已经有 `config` 字段可以存储 `stage_id`

**建议**: 保持原始 step_id，在 `config.stage_id` 中记录所属 stage。

---

#### 问题 3：契约解析是运行时问题，不是模板加载问题 🔴

**方案中的处理**:
```python
# 在模板加载时提取契约路径
contracts = self._extract_contracts(doc)
```

**批判**: 契约路径是**相对路径**，需要在运行时解析:

```yaml
path: "../../../prd/contracts/frozen-detailed-prd-contract/v1/schema.json"
# 相对于 workflow.yaml 的位置，不是相对于项目根目录
```

方案没有说明:
1. 这些相对路径何时被解析为绝对路径？
2. 如果契约文件不存在，工作流是否应该启动失败？
3. 契约内容如何传递给 Agent？直接传文件路径还是加载内容？

**真正的问题**: Orchestrator 需要在**创建工作流实例时**接收契约路径，而不是在加载模板时。

---

#### 问题 4：变量引用解析与依赖关系混淆 🟡

**方案中的处理**:
```python
# RuntimeResolver 解析 $inputs.prd
def resolve(self, value, context):
    if value.startswith("$inputs."):
        return context["inputs"].get(key)
```

**批判**: 变量引用有两层含义，方案只解决了一层:

| 引用类型 | 时机 | 方案是否处理 |
|---------|------|-------------|
| `$inputs.prd` | 运行时解析值 | ✅ 是 |
| `$s3_1_extract_features.feature_list` | 建立 DAG 依赖 | ❌ 否 |

当 step 引用另一个 step 的输出时，需要:
1. 建立 `depends_on` 关系（DAG 构建时）
2. 解析实际值（运行时）

方案只做了解析值，没有自动建立依赖关系。这意味着如果 spec-global 工作流中遗漏了 `depends_on` 字段，转换后的步骤可能并行执行，导致错误。

---

#### 问题 5：门禁系统集成的"半吊子"方案 🔴

**方案中的处理**:
```python
def _parse_gate(self, gate_def: Dict[str, Any]) -> Optional[str]:
    ref = gate_def.get("ref", "")
    if ref:
        parts = ref.split(".")
        return parts[-1]  # design_input_gate
```

**批判**: 这只是提取了 gate ID，但没有:

1. **加载门禁定义**: 从 `../../gates/design-input-gate/v1/gate.yaml` 读取门禁规则
2. **门禁条件判断**: 什么时候触发门禁？
3. **门禁失败处理**: `on_fail.action: block_and_report` 如何实现？

spec-global 的门禁系统是**外部化、可复用**的，Orchestrator 的门禁是**内联**的。两者不是同一个概念。

---

#### 问题 6：测试用例设计工作流的核心特性无法适配 🔴

spec-global 的测试用例设计工作流有以下特性，Orchestrator **无法支持**:

| 特性 | spec-global | Orchestrator | 可行性 |
|------|-------------|--------------|--------|
| 人类审批循环 | review → 评审不通过 → revision → 重新 review | 单向 DAG，无回退 | ❌ 不可能 |
| 条件执行 | `condition: "consistency_matrix.conflicts > 0"` | 无条件分支 | ❌ 不可能 |
| 超时处理 | `timeout: 72h` | 无超时机制 | ❌ 需要新功能 |
| 并行 stage | 多个 stage 同时执行 | 支持（depends_on） | ✅ 可行 |

**结论**: 即使实现了格式转换，这个工作流也无法在 Orchestrator 上正确执行。

---

### 5.2 架构层面的问题

#### 问题 7：双格式支持的技术债 🟡

引入适配器意味着:

1. **永久维护两套格式**: 每次新功能都需要同时适配两种格式
2. **调试困难**: 问题发生在转换层还是执行层？
3. **语义丢失风险**: 转换过程可能丢失 spec-global 的某些语义
4. **格式分歧**: 未来新工作流用哪种格式？

**历史经验**: 类似的适配层最终都会变成"没人敢动的雷区"。

---

#### 问题 8：根本问题不是格式，是缺乏统一标准 🔴

当前情况是:

```
┌─────────────────────────────────────────────────────────────┐
│                     LEE 框架现状                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ Orchestrator 格式│         │ spec-global 格式  │         │
│  │   (examples/)    │         │ (spec-global/)   │         │
│  └──────────────────┘         └──────────────────┘         │
│           │                            │                     │
│           │    没有统一的工作流定义标准        │              │
│           │                            │                     │
│           └────────────┬───────────────┘                     │
│                        │                                     │
│                        ▼                                     │
│              ┌──────────────────┐                           │
│              │   适配器层（方案）  │  ← 治标不治本              │
│              └──────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

**真正需要的**: 统一的工作流定义标准 + 明确的迁移路径。

---

### 5.3 评审总结

| 维度 | 评分 | 说明 |
|------|------|------|
| **技术可行性** | ⭐⭐ | 适配器方案技术上可行，但无法解决核心问题 |
| **架构合理性** | ⭐⭐ | 引入不必要的抽象层，增加系统复杂度 |
| **维护成本** | ⭐ | 双格式支持会带来永久的技术债 |
| **用户体验** | ⭐⭐⭐ | 用户可以"跑起来"，但可能遇到运行时错误 |
| **长远价值** | ⭐ | 治标不治本，推迟真正需要解决的问题 |

---

## 6. 替代方案设计

### 方案 A：格式统一 + 迁移工具（推荐 ⭐⭐⭐⭐⭐）

**核心思路**: 承认 spec-global 格式是未来方向，让 Orchestrator 原生支持它。

#### 阶段 1：扩展 Orchestrator 支持企业级特性

```python
# 1. 扩展 Step 模型
@dataclass
class Step:
    # ... 现有字段
    condition: Optional[str] = None  # 新增：执行条件
    timeout_seconds: Optional[int] = None  # 新增：超时
    on_failure: Optional[Dict] = None  # 新增：失败处理

# 2. 扩展 WorkflowTemplate
@dataclass
class WorkflowTemplate:
    # ... 现有字段
    state_machine: Optional[Dict] = None  # 新增：显式状态机
    contracts: Optional[Dict] = None  # 新增：契约定义
    gates: Optional[Dict] = None  # 新增：门禁定义

# 3. 扩展 Orchestrator 执行引擎
class Orchestrator:
    async def _run_step(self, step_id: str) -> StepResult:
        # 检查执行条件
        if not self._evaluate_condition(step.condition):
            return StepResult(status="skipped", ...)

        # 设置超时
        timeout = step.timeout_seconds or self._default_timeout

        # 执行并处理失败
        try:
            result = await asyncio.wait_for(self._execute_step(step), timeout)
        except asyncio.TimeoutError:
            return self._handle_timeout(step, step.on_failure)
```

#### 阶段 2：TemplateManager 直接解析 spec-global

不需要适配器，直接在 `_parse_template_doc` 中处理:

```python
def _parse_template_doc(self, doc: Dict, template_id: str) -> WorkflowTemplate:
    if doc.get("kind") == "workflow":
        # spec-global 格式：直接解析
        return WorkflowTemplate(
            id=doc["id"],
            level=self._infer_level(doc),
            name=doc["name"],
            description=doc["description"],
            steps=self._flatten_steps(doc["stages"]),  # 内联展平
            state_machine=doc.get("state_machine"),
            contracts=self._parse_contracts(doc.get("contracts")),
            gates=self._parse_gates(doc.get("gates")),
            ...
        )
```

#### 阶段 3：迁移旧格式

提供迁移工具:

```bash
# CLI 命令
lee migrate-workflow examples/templates.yaml spec-global/workflows/
```

**优势**:
- 一劳永逸解决格式问题
- spec-global 的完整特性得以保留
- 长期维护成本最低

**劣势**:
- 需要重构 Orchestrator 执行引擎
- 实施周期较长（4-6周）

---

### 方案 B：双执行器模式（备选 ⭐⭐⭐）

**核心思路**: 承认 Orchestrator 无法执行 spec-global 工作流，为其创建专用执行器。

```python
class SpecGlobalWorkflowExecutor:
    """
    spec-global 工作流专用执行器

    特性：
    - 支持显式状态机
    - 支持条件分支
    - 支持人类审批循环
    - 支持超时处理
    """

    def __init__(self, store, template_manager, event_bus):
        self.store = store
        self.template_manager = template_manager
        self.event_bus = event_bus
        self.state_machine = StateMachineEngine()  # 新增状态机引擎

    async def execute(self, workflow_id: str):
        """执行 spec-global 工作流"""
        template = self.template_manager.get_template(workflow_id)
        state_def = template.state_machine

        # 使用状态机驱动执行
        await self.state_machine.run(
            initial_state="INIT",
            transitions=state_def["transitions"],
            action_handler=self._execute_state_action
        )
```

**优势**:
- 不破坏 Orchestrator 现有架构
- 可以为 spec-global 工作流实现完整的特性
- 两种执行器可以并存

**劣势**:
- 需要维护两套执行引擎
- 用户体验不统一（不同的工作流用不同的执行器）

---

### 方案 C：拒绝执行 + 清晰错误信息（最小方案 ⭐⭐）

**核心思路**: 暂时不支持 spec-global 工作流，给用户清晰的错误信息。

```python
class Orchestrator:
    async def create_workflow(self, level, template_id, ...):
        template = self.template_manager.get_template(template_id)

        # 检测 spec-global 格式
        if template.state_machine or template.contracts:
            raise UnsupportedFormatError(
                f"Template '{template_id}' uses spec-global format "
                f"which is not yet supported by Orchestrator.\n"
                f"Please use the simplified format defined in examples/templates.yaml\n"
                f" or use the SpecGlobalWorkflowExecutor (coming soon)."
            )
```

**优势**:
- 最小变更
- 诚实面对用户
- 争取时间实现方案 A 或 B

**劣势**:
- 用户无法使用 spec-global 工作流
- 可能阻塞 QA 团队工作

---

### 方案对比矩阵

| 维度 | 原方案（适配器） | 方案 A（格式统一） | 方案 B（双执行器） | 方案 C（拒绝执行） |
|------|-----------------|-------------------|-------------------|-------------------|
| **实施周期** | 2-3周 | 4-6周 | 3-4周 | 1周 |
| **技术可行性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **架构合理性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **维护成本** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **用户体验** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **长远价值** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **推荐指数** | ❌ 不推荐 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

---

## 7. 最终建议

### 7.1 推荐行动路线

```
┌─────────────────────────────────────────────────────────────┐
│                      行动路线图                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐                                       │
│  │  立即 (1周)      │                                       │
│  │  方案 C：拒绝执行  │  → 给用户清晰的错误信息，争取时间        │
│  └────────┬─────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           短期决策点 (产品+技术团队)                  │   │
│  │                                                       │   │
│  │  问: Orchestrator 是否需要支持人类审批循环？          │   │
│  │  问: spec-global 是否是官方标准？                     │   │
│  │  问: 是否接受双执行器并存？                           │   │
│  └───────────────┬───────────────────────────────────────┘   │
│                  │                                           │
│         ┌────────┴────────┐                                 │
│         ▼                 ▼                                 │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ 方案 A       │  │ 方案 B       │                        │
│  │ 格式统一     │  │ 双执行器     │                        │
│  │ (4-6周)      │  │ (3-4周)      │                        │
│  └──────────────┘  └──────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 分阶段实施建议

#### 第 1 周：立即行动

1. **实施方案 C**：添加格式检测和清晰错误信息
2. **文档更新**：说明当前支持的格式和限制
3. **需求收集**：与 QA 团队确认测试用例设计工作流的必需特性

#### 第 2 周：决策准备

1. **技术调研**：评估方案 A 和方案 B 的详细工作量
2. **原型验证**：为关键特性（状态机、人类审批）做原型
3. **风险评估**：评估每个方案的风险和缓解措施

#### 第 3 周：决策会议

召开产品+技术团队决策会议，回答以下问题（见第 8 节）。

#### 第 4+ 周：实施选定方案

根据决策结果，实施方案 A 或方案 B。

---

## 8. 决策检查清单

在决定最终方案前，需要回答以下问题：

### 8.1 产品层面

| 问题 | 为什么重要 | 需要的回答 |
|------|-----------|-----------|
| 测试用例设计工作流是否必需支持人类审批循环？ | 决定是否需要状态机引擎 | [ ] 是，必须有 / [ ] 可以简化 / [ ] 不确定 |
| 测试用例设计工作流是否必需支持条件分支？ | 决定执行引擎复杂度 | [ ] 是，必须有 / [ ] 可以简化 / [ ] 不确定 |
| spec-global 格式是否是官方标准？ | 决定迁移方向 | [ ] 是，未来都用这个 / [ ] 不是，可选 / [ ] 不确定 |
| 有多少旧格式工作流需要迁移？ | 决定迁移成本 | [ ] 数量：___ 个 |
| 测试用例设计工作流可以简化吗？ | 决定是否需要完整特性 | [ ] 可以简化到 DAG / [ ] 不能简化 / [ ] 不确定 |

### 8.2 技术层面

| 问题 | 为什么重要 | 需要的回答 |
|------|-----------|-----------|
| 是否接受双执行器并存？ | 决定方案 B 的可行性 | [ ] 可接受 / [ ] 不可接受 / [ ] 需要更多讨论 |
| 扩展 Orchestrator 的风险可控吗？ | 决定方案 A 的可行性 | [ ] 风险可控 / [ ] 风险太高 / [ ] 需要更多评估 |
| 多少时间可用于实施？ | 决定选择哪个方案 | [ ] 1-2周 / [ ] 3-4周 / [ ] 5-6周+ |
| 团队技能是否支持状态机引擎开发？ | 决定技术可行性 | [ ] 是 / [ ] 否 / [ ] 需要培训 |

### 8.3 业务层面

| 问题 | 为什么重要 | 需要的回答 |
|------|-----------|-----------|
| QA 团队可以等多久？ | 决定紧急程度 | [ ] 1周 / [ ] 2-4周 / [ ] 1-2月 |
| 是否有替代方案可以临时使用？ | 决定是否可以等待 | [ ] 有（___） / [ ] 无 / [ ] 不确定 |
| 不支持 spec-global 工作流的业务影响？ | 决定优先级 | [ ] 高 / [ ] 中 / [ ] 低 |

### 8.4 决策矩阵

根据以上问题的回答，使用以下决策矩阵：

| 如果... | 推荐... | 优先级 |
|---------|---------|--------|
| 需要人类审批循环 + 条件分支 + spec-global 是标准 | 方案 A（格式统一） | P0 |
| 需要完整特性但不能接受 Orchestrator 重构 | 方案 B（双执行器） | P0 |
| 可以简化工作流 + 有足够时间 | 方案 A（格式统一） | P1 |
| 没有足够时间 + 可以临时使用旧格式 | 方案 C（拒绝执行） | P1 |

---

## 9. 附录

### 9.1 术语表

| 术语 | 定义 |
|------|------|
| spec-global 格式 | 企业级工作流定义格式，包含 stages、state_machine、contracts 等完整特性 |
| Orchestrator 格式 | 简化版工作流定义格式，基于 DAG 依赖驱动 |
| 适配器层 | 连接两种格式的中间层，负责格式转换 |
| 状态机引擎 | 驱动显式状态转换的执行引擎 |
| 契约绑定 | 将外部契约文件路径绑定到工作流实例的过程 |

### 9.2 参考文档

1. `spec-global/departments/qa/workflows/test-case-design-pipeline/v1/workflow.yaml` - spec-global 工作流示例
2. `examples/templates.yaml` - Orchestrator 格式示例
3. `src/lee/orchestrator/execution/template_manager.py` - 模板管理器实现
4. `src/lee/orchestrator/execution/orchestrator.py` - Orchestrator 实现
5. `src/lee/orchestrator/storage/models.py` - 数据模型定义

### 9.3 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-02-05 | 初始版本，包含完整分析和评审 | 架构团队 |

---

**文档状态**: 待决策

**下一步行动**: 安排决策会议，回答第 8 节中的问题

**联系方式**: 如有疑问，请联系架构团队
