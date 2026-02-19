---
title: LEE 框架 spec-global 迁移实施方案
author: LEE Team
date: 2026-02-06
version: 1.0
last_updated: 2026-02-19
---

# LEE 框架 spec-global 迁移实施方案

> **版本**: 1.0
> **创建日期**: 2026-02-05
> **状态**: 🚧 实施中
> **负责人**: LEE Core Team

---

## 📋 文档概览

本文档定义了将 spec-global 规范完全集成到 LEE Orchestrator 的完整实施方案。spec-global 是 LEE 框架中定义工作流、Agent、Skill、Gate 和契约的规范体系，而 Orchestrator 是实际执行这些工作流的引擎。

**核心问题**: spec-global 定义了丰富的特性（状态机、门禁规则、条件执行、变量引用等），但当前 Orchestrator 仅支持基础的工作流执行，存在显著的特性覆盖差距。

**实施目标**: 建立从 spec-global YAML 到 Orchestrator 执行的完整链路，确保规范定义的语义能够准确地在执行引擎中实现。

---

## 📐 宪法级约束

以下三条原则是本实施方案的不可违背的约束：

### 约束 1: 单一数据源权威（Single Source of Truth）

> **spec-global YAML 是唯一的规范定义来源，Orchestrator 是唯一的执行权威**

- ✅ 允许：解析器将 spec-global YAML 转换为内部 IR（中间表示）
- ❌ 禁止：在 Orchestrator 中硬编码任何 spec-global 的语义规则
- ✅ 允许：通过 IR 进行优化和执行
- ❌ 禁止：任何绕过 spec-global 的"捷径执行"

**理由**：确保规范和实现的一致性，避免"代码即文档"的分裂问题。

---

### 约束 2: 向后兼容性（Backward Compatibility）

> **现有 Orchestrator API 和执行模式必须保持 100% 兼容**

- ✅ 允许：新增解析器和 IR 转换层
- ✅ 允许：扩展内部数据结构
- ❌ 禁止：破坏现有 API 签名
- ❌ 禁止：改变现有工作流的执行语义

**理由**：已有项目正在使用 Orchestrator，不能破坏其稳定性。

---

### 约束 3: 渐进式迁移（Progressive Migration）

> **分阶段实施，每阶段都是可独立交付和验证的增量**

- ✅ 允许：暂时保留双轨制（旧格式 + 新格式）
- ✅ 允许：通过特性开关控制新特性启用
- ❌ 禁止："大爆炸"式重写
- ❌ 禁止：任何无法独立验证的阶段交付

**理由**：降低风险，确保每一步都有可见的进展和回滚能力。

---

## 🎯 能力矩阵：spec-global 特性 vs Orchestrator 支持

### 特性分类说明

- ✅ **完全支持**：已实现并验证
- 🟡 **部分支持**：有基础实现，但缺少完整语义
- ❌ **不支持**：完全未实现
- 🚧 **实施中**：正在开发中
- 📋 **计划中**：已列入计划

---

### 核心特性支持状态

| 特性类别 | 特性名称 | spec-global 定义 | Orchestrator 支持 | 差距评估 | 优先级 |
|---------|---------|-----------------|------------------|---------|--------|
| **工作流结构** | kind/version | ✅ 已定义 | ❌ 未验证 | 需添加版本校验 | P2 |
| | stages/steps | ✅ 8 stages, 21 steps | 🟡 基础支持 | stages 未解析为步骤 | P0 |
| | state_machine | ✅ 11 状态 | ❌ 仅支持基础状态 | 完整状态机未实现 | P0 |
| **条件执行** | conditional steps | ✅ type: conditional | ❌ 不支持 | 条件解析引擎缺失 | P1 |
| | depends_on | ✅ 依赖定义 | 🟡 部分支持 | 依赖解析不完整 | P1 |
| | for_each | ✅ 循环执行 | ❌ 不支持 | 循环语义未实现 | P2 |
| **门禁系统** | gate rules | ✅ 复杂规则系统 | ❌ 仅基础 gate | 规则引擎缺失 | P0 |
| | mandatory criteria | ✅ 强制标准 | ❌ 不支持 | 标准验证缺失 | P0 |
| | threshold criteria | ✅ 阈值标准 | ❌ 不支持 | 阈值检查缺失 | P0 |
| | exemption policy | ✅ 豁免管理 | ❌ 不支持 | 豁免逻辑缺失 | P1 |
| | signoff requirements | ✅ 签字流程 | ❌ 不支持 | 审批链缺失 | P1 |
| **契约系统** | inputs/outputs | ✅ 4 输入/3 输出 | 🟡 部分支持 | 契约验证不完整 | P1 |
| | contract schema | ✅ 契约引用 | ❌ 不支持 | Schema 验证缺失 | P1 |
| | structure validation | ✅ 结构验证 | ❌ 不支持 | 验证器缺失 | P2 |
| **变量系统** | variable reference | ✅ $inputs.prd | ❌ 不支持 | 变量解析器缺失 | P0 |
| | step outputs | ✅ $s2_1.xxx | ❌ 不支持 | 输出引用缺失 | P0 |
| | conditional expr | ✅ condition 表达式 | ❌ 不支持 | 表达式求值缺失 | P1 |
| **人类介入** | human_gate | ✅ 定义完整 | 🟡 基础实现 | checklist 未支持 | P1 |
| | approval criteria | ✅ 审批标准 | ❌ 不支持 | 标准检查缺失 | P1 |
| | timeout/escalate | ✅ 超时升级 | ❌ 不支持 | 超时处理缺失 | P2 |

---

### 关键差距分析

#### 🔴 关键差距（P0 - 必须立即解决）

1. **状态机执行**
   - spec-global 定义 11 个状态的完整状态转换
   - Orchestrator 仅支持 PENDING/RUNNING/COMPLETED/FAILED
   - **影响**：无法表达复杂的工作流状态转换逻辑

2. **门禁规则引擎**
   - spec-global 定义强制标准、阈值标准、豁免管理
   - Orchestrator 仅支持基础的 gate 概念
   - **影响**：无法实现质量门禁的核心功能

3. **变量解析**
   - spec-global 支持复杂的变量引用（$inputs, $sX_Y, 条件表达式）
   - Orchestrator 完全不支持变量解析
   - **影响**：无法实现步骤间的数据传递

#### 🟡 重要差距（P1 - 1-2 周内解决）

4. **条件执行**
   - spec-global 支持 conditional steps
   - Orchestrator 无法根据条件跳过步骤
   - **影响**：无法实现动态工作流

5. **契约验证**
   - spec-global 定义了完整的契约 schema
   - Orchestrator 缺少契约验证逻辑
   - **影响**：无法保证输入输出的质量

6. **审批链管理**
   - spec-global 定义了复杂的审批流程
   - Orchestrator 的 human_gate 实现过于简化
   - **影响**：无法实现企业级审批流程

---

## 📅 分阶段实施计划

### P0: 止血 + 单一标准地基（2 天）

**目标**：建立 IR 结构和基础解析器，确保最复杂的 QA 工作流可以被解析。

#### 阶段 P0.1：IR 结构设计（4 小时）

**交付物**：
- [ ] 定义 IR 数据模型（Python dataclass）
  - `WorkflowIR`: 工作流中间表示
  - `StateMachineIR`: 状态机定义
  - `GateIR`: 门禁规则
  - `StepIR`: 步骤定义（包含条件）
  - `VariableIR`: 变量引用

**验证标准**：
- 能够表达 QA 工作流的所有结构元素
- 通过类型检查（mypy strict mode）

#### 阶段 P0.2：YAML 解析器（8 小时）

**交付物**：
- [ ] 实现 `SpecGlobalParser` 类
  - 解析 workflow.yaml 的 kind/version/stages/steps
  - 解析 state_machine 的状态和转换
  - 解析 gates 的规则定义
  - 解析 inputs/outputs 契约引用

**验证标准**：
- 能够成功解析 `test-case-design-pipeline/v1/workflow.yaml`
- 解析结果通过 IR 验证
- 单元测试覆盖率 >= 90%

#### 阶段 P0.3：变量解析器（4 小时）

**交付物**：
- [ ] 实现 `VariableResolver` 类
  - 解析 `$inputs.xxx` 引用
  - 解析 `$sX_Y_zzz` 步骤输出引用
  - 支持嵌套路径访问

**验证标准**：
- 能够解析 QA 工作流中的所有变量引用
- 提供清晰的错误信息（变量未定义）

#### 阶段 P0.4：基础集成（4 小时）

**交付物**：
- [ ] 修改 `TemplateManager._parse_template_doc`
  - 检测 `kind: workflow` 规范
  - 调用 SpecGlobalParser 解析
  - 转换为 WorkflowTemplate

**验证标准**：
- QA 工作流可以被加载为 Template
- 保持向后兼容（旧格式仍可工作）

---

### P1: QA 优先完整支持（1-2 周）

**目标**：完整支持 QA 工作流的执行，包括状态机、门禁规则、人类审批。

#### 阶段 P1.1：状态机执行引擎（3 天）

**交付物**：
- [ ] 扩展 `WorkflowStateMachine`
  - 支持 11 个状态的完整定义
  - 实现状态转换逻辑
  - 支持 BLOCKED 状态和恢复

**验证标准**：
- QA 工作流的状态转换正确执行
- 支持状态查询和可视化
- 单元测试覆盖所有状态转换路径

#### 阶段 P1.2：门禁规则引擎（4 天）

**交付物**：
- [ ] 实现 `GateRuleEngine` 类
  - 强制标准验证（0 容忍）
  - 阈值标准检查（可警告但继续）
  - 风险可接受标准（需签字）
  - 豁免管理逻辑

**验证标准**：
- `design-input-gate` 规则完全实现
- `test-case-review-gate` 规则完全实现
- 规则评估结果可追溯

#### 阶段 P1.3：条件执行支持（2 天）

**交付物**：
- [ ] 扩展 `get_ready_steps` 逻辑
  - 评估 conditional steps 的 condition
  - 支持布尔表达式求值
  - 跳过不满足条件的步骤

**验证标准**：
- QA 工作流的条件步骤正确跳过/执行
- 表达式求值支持 AND/OR/比较运算符

#### 阶段 P1.4：人类审批增强（3 天）

**交付物**：
- [ ] 增强 Human Gate 实现
  - 支持审批链（多角色签字）
  - 实现 checklist 验证
  - 支持 timeout 和 escalate
  - 审批历史记录

**验证标准**：
- QA 工作流的人类审批流程完整执行
- 审批决策可追溯
- 超时自动升级

---

### P2: 并行推进（逐部门兼容）（2-4 周）

**目标**：支持所有部门的工作流，包括 Dev、PRD、UI、DevOps 等。

#### 阶段 P2.1：Dev 部门支持（1 周）

**交付物**：
- [ ] 解析 `development-pipeline` 工作流
- [ ] 支持 Phase 并行执行
- [ ] 支持子工作流 spawn

#### 阶段 P2.2：PRD 部门支持（3 天）

**交付物**：
- [ ] 解析 `product-pipeline` 工作流
- [ ] 支持人类冻结点

#### 阶段 P2.3：UI 部门支持（3 天）

**交付物**：
- [ ] 解析 `ui-design-pipeline` 工作流

#### 阶段 P2.4：DevOps 部门支持（3 天）

**交付物**：
- [ ] 解析 `devops-deployment` 工作流
- [ ] 支持部署脚本执行

---

### P3: 根源性预防（持续）

**目标**：建立完善的测试、文档和工具，防止未来的退化。

#### 阶段 P3.1：测试套件（持续）

**交付物**：
- [ ] 单元测试（每个模块覆盖率 >= 90%）
- [ ] 集成测试（端到端工作流执行）
- [ ] 真实项目验证（已有项目迁移验证）

#### 阶段 P3.2：文档和工具（持续）

**交付物**：
- [ ] spec-global 规范文档
- [ ] Orchestrator 集成指南
- [ ] 调试工具（工作流可视化、状态查询）

---

## 🔧 详细技术方案

### 1. 内部 IR 结构设计

#### 1.1 核心 IR 定义

```python
# src/lee/orchestrator/ir/models.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum

class IRKind(Enum):
    """IR 类型枚举"""
    WORKFLOW = "workflow"
    STATE_MACHINE = "state_machine"
    STEP = "step"
    GATE = "gate"
    VARIABLE = "variable"
    CONTRACT = "contract"

@dataclass
class VariableIR:
    """变量引用中间表示"""
    reference: str  # 原始引用，如 "$inputs.prd"
    source_type: str  # "inputs" | "step" | "context"
    path: List[str]  # 解析后的路径，如 ["prd"]
    step_id: Optional[str] = None  # 如果引用步骤输出

    def __post_init__(self):
        """验证引用格式"""
        if not self.reference.startswith("$"):
            raise ValueError(f"Invalid variable reference: {self.reference}")

@dataclass
class GateRuleIR:
    """门禁规则中间表示"""
    rule_id: str
    name: str
    rule_type: str  # "mandatory" | "threshold" | "risk_acceptance"
    rule_expression: str  # 规则表达式
    severity: str  # "blocker" | "major" | "minor"
    exemption_allowed: bool
    validation_method: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class GateIR:
    """门禁中间表示"""
    gate_id: str
    name: str
    description: str
    mandatory_criteria: List[GateRuleIR]
    threshold_criteria: List[GateRuleIR]
    risk_acceptance_criteria: List[GateRuleIR]
    exemption_policy: Dict[str, Any]
    signoff_requirements: Dict[str, Any]

    def evaluate(self, context: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        评估门禁规则

        Returns:
            (passed, issues): 通过标志和问题列表
        """
        issues = []

        # 评估强制标准（0 容忍）
        for rule in self.mandatory_criteria:
            if not self._evaluate_rule(rule, context):
                issues.append(f"[MANDATORY] {rule.name}: {rule.error_message}")

        # 如果有强制标准失败，直接返回
        mandatory_failures = [i for i in issues if i.startswith("[MANDATORY]")]
        if mandatory_failures:
            return False, issues

        # 评估阈值标准
        for rule in self.threshold_criteria:
            if not self._evaluate_rule(rule, context):
                issues.append(f"[THRESHOLD] {rule.name}: 警告")

        return True, issues

    def _evaluate_rule(self, rule: GateRuleIR, context: Dict[str, Any]) -> bool:
        """评估单个规则（简化版，实际需要完整的表达式引擎）"""
        # TODO: 实现完整的表达式求值
        return True

@dataclass
class StepIR:
    """步骤中间表示"""
    id: str
    kind: str  # "agent" | "skill" | "human_gate" | "conditional"
    name: str
    description: str
    stage_id: Optional[str] = None

    # 执行配置
    agent_id: Optional[str] = None
    skill_id: Optional[str] = None
    executor_type: Optional[str] = None
    execution: Optional[Dict[str, Any]] = None

    # 依赖和条件
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None  # 条件表达式
    parallel_with: List[str] = field(default_factory=list)

    # 输入输出
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)

    # 门禁
    gate: Optional[GateIR] = None
    post_gate: Optional[GateIR] = None
    human_gate: Optional[str] = None

    # 其他配置
    config: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self, completed_steps: List[str], context: Dict[str, Any]) -> bool:
        """检查步骤是否就绪"""
        # 检查依赖
        for dep in self.depends_on:
            if dep not in completed_steps:
                return False

        # 检查条件
        if self.condition:
            if not self._evaluate_condition(context):
                return False

        return True

    def _evaluate_condition(self, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        # TODO: 实现完整的表达式求值
        return True

@dataclass
class StateTransitionIR:
    """状态转换中间表示"""
    from_state: str
    to_state: str
    trigger: str
    note: Optional[str] = None

@dataclass
class StateMachineIR:
    """状态机中间表示"""
    states: List[str]
    transitions: Dict[str, List[StateTransitionIR]]
    initial_state: str = "INIT"

    def get_next_states(self, current_state: str, trigger: str) -> List[str]:
        """获取触发后的下一个状态"""
        if current_state not in self.transitions:
            return []

        next_states = []
        for transition in self.transitions[current_state]:
            if transition.trigger == trigger:
                next_states.append(transition.to_state)

        return next_states

@dataclass
class ContractIR:
    """契约中间表示"""
    contract_id: str
    kind: str  # "input" | "output"
    path: str
    description: str
    required: bool = True
    structure: Optional[str] = None

@dataclass
class WorkflowIR:
    """工作流中间表示"""
    id: str
    kind: str
    version: str
    name: str
    description: str
    owner: str
    tags: List[str]

    # 契约
    inputs: List[ContractIR]
    outputs: List[ContractIR]

    # 状态机
    state_machine: Optional[StateMachineIR] = None

    # 步骤
    steps: List[StepIR] = field(default_factory=list)
    stages: List[Dict[str, Any]] = field(default_factory=list)

    # 门禁
    gates: Dict[str, GateIR] = field(default_factory=dict)

    # 人类介入
    human_in_the_loop: List[Dict[str, Any]] = field(default_factory=list)

    # 其他配置
    config: Dict[str, Any] = field(default_factory=dict)

    def get_step_by_id(self, step_id: str) -> Optional[StepIR]:
        """根据 ID 获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ready_steps(self, completed_steps: List[str], context: Dict[str, Any]) -> List[StepIR]:
        """获取就绪的步骤"""
        ready = []
        for step in self.steps:
            if step.is_ready(completed_steps, context):
                ready.append(step)
        return ready
```

#### 1.2 IR 转换器

```python
# src/lee/orchestrator/ir/converter.py

from lee.orchestrator.ir.models import *
from lee.orchestrator.storage.models import WorkflowTemplate, Step

class IRConverter:
    """IR 和现有模型之间的转换器"""

    @staticmethod
    def ir_to_template(ir: WorkflowIR) -> WorkflowTemplate:
        """将 IR 转换为 WorkflowTemplate"""
        steps = [IRConverter._ir_to_step(step_ir) for step_ir in ir.steps]

        return WorkflowTemplate(
            id=ir.id,
            level=WorkflowLevel.DEPARTMENT,  # 根据 kind 推断
            name=ir.name,
            description=ir.description,
            steps=steps,
            config=ir.config,
        )

    @staticmethod
    def _ir_to_step(step_ir: StepIR) -> Step:
        """将 StepIR 转换为 Step"""
        return Step(
            id=step_ir.id,
            kind=step_ir.kind,
            executor_type=step_ir.executor_type,
            agent_id=step_ir.agent_id,
            skill_id=step_ir.skill_id,
            gate_id=step_ir.human_gate,
            depends_on=step_ir.depends_on,
            input={"params": step_ir.inputs} if step_ir.inputs else {},
            outputs=[],  # TODO: 转换 outputs
            config=step_ir.config,
        )
```

---

### 2. 解析器实现方案

#### 2.1 SpecGlobal 解析器

```python
# src/lee/orchestrator/execution/spec_global_parser.py

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from lee.orchestrator.ir.models import *

class SpecGlobalParser:
    """spec-global YAML 解析器"""

    def __init__(self):
        self.version = "1.0"

    def parse_workflow_file(self, file_path: str) -> WorkflowIR:
        """解析工作流 YAML 文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        docs = list(yaml.safe_load_all(content))
        main_doc = docs[0]

        return self.parse_workflow(main_doc)

    def parse_workflow(self, doc: Dict[str, Any]) -> WorkflowIR:
        """解析工作流文档"""
        # 验证 kind 和 version
        kind = doc.get("kind")
        if kind != "workflow":
            raise ValueError(f"Expected kind=workflow, got {kind}")

        # 解析基本信息
        workflow_ir = WorkflowIR(
            id=doc["id"],
            kind=kind,
            version=doc["version"],
            name=doc["name"],
            description=doc.get("description", ""),
            owner=doc.get("owner", ""),
            tags=doc.get("tags", []),
            inputs=self._parse_contracts(doc, "inputs"),
            outputs=self._parse_contracts(doc, "outputs"),
        )

        # 解析状态机
        if "state_machine" in doc:
            workflow_ir.state_machine = self._parse_state_machine(doc["state_machine"])

        # 解析步骤
        if "stages" in doc:
            workflow_ir.stages = doc["stages"]
            for stage in doc["stages"]:
                for step_data in stage.get("steps", []):
                    step_ir = self._parse_step(step_data, stage["id"])
                    workflow_ir.steps.append(step_ir)
        elif "steps" in doc:
            for step_data in doc["steps"]:
                step_ir = self._parse_step(step_data)
                workflow_ir.steps.append(step_ir)

        # 解析门禁
        if "gates" in doc:
            for gate_id, gate_path in doc["gates"].items():
                gate_ir = self._parse_gate_file(gate_path)
                workflow_ir.gates[gate_id] = gate_ir

        # 解析人类介入
        if "human_in_the_loop" in doc:
            workflow_ir.human_in_the_loop = doc["human_in_the_loop"]

        return workflow_ir

    def _parse_contracts(self, doc: Dict[str, Any], key: str) -> List[ContractIR]:
        """解析契约定义"""
        contracts = []
        contracts_section = doc.get("contracts", {}).get(key, [])

        for contract_def in contracts_section:
            if isinstance(contract_def, dict):
                for contract_id, contract_spec in contract_def.items():
                    contracts.append(ContractIR(
                        contract_id=contract_id,
                        kind=key.rstrip("s"),  # inputs -> input
                        path=contract_spec.get("path", ""),
                        description=contract_spec.get("description", ""),
                        required=contract_spec.get("required", True),
                        structure=contract_spec.get("structure"),
                    ))

        return contracts

    def _parse_state_machine(self, sm_data: Dict[str, Any]) -> StateMachineIR:
        """解析状态机定义"""
        states = [s["id"] if isinstance(s, dict) else s for s in sm_data["states"]]
        transitions = {}

        for state, transitions_list in sm_data.get("transitions", {}).items():
            transitions[state] = []
            for trans in transitions_list:
                transitions[state].append(StateTransitionIR(
                    from_state=state,
                    to_state=trans["to"],
                    trigger=trans["trigger"],
                    note=trans.get("note"),
                ))

        return StateMachineIR(
            states=states,
            transitions=transitions,
            initial_state=sm_data["states"][0]["id"] if isinstance(sm_data["states"][0], dict) else sm_data["states"][0],
        )

    def _parse_step(self, step_data: Dict[str, Any], stage_id: Optional[str] = None) -> StepIR:
        """解析步骤定义"""
        step_ir = StepIR(
            id=step_data["id"],
            kind=step_data.get("type", "agent"),  # agent | conditional | human_decision
            name=step_data.get("name", ""),
            description=step_data.get("description", ""),
            stage_id=stage_id,
            agent_id=step_data.get("run"),
            skill_id=step_data.get("skill"),
            execution=step_data.get("execution"),
            depends_on=step_data.get("dependencies", {}).get("requires", []),
            condition=step_data.get("condition"),
            inputs=step_data.get("inputs", []),
            outputs=step_data.get("outputs", []),
            config={"description": step_data.get("description")},
        )

        # 解析 gate
        if "gate" in step_data:
            gate_ref = step_data["gate"]
            if isinstance(gate_ref, dict):
                step_ir.gate = self._parse_gate_inline(gate_ref)
            elif isinstance(gate_ref, str):
                step_ir.human_gate = gate_ref

        return step_ir

    def _parse_gate_file(self, gate_path: str) -> GateIR:
        """解析门禁文件（简化版，实际需要解析 gate.yaml）"""
        # TODO: 实现完整的门禁文件解析
        return GateIR(
            gate_id=gate_path,
            name="Gate",
            description="",
            mandatory_criteria=[],
            threshold_criteria=[],
            risk_acceptance_criteria=[],
            exemption_policy={},
            signoff_requirements={},
        )

    def _parse_gate_inline(self, gate_data: Dict[str, Any]) -> GateIR:
        """解析内联门禁定义"""
        return GateIR(
            gate_id=gate_data.get("id", ""),
            name=gate_data.get("name", ""),
            description=gate_data.get("description", ""),
            mandatory_criteria=[],
            threshold_criteria=[],
            risk_acceptance_criteria=[],
            exemption_policy={},
            signoff_requirements={},
        )
```

#### 2.2 变量解析器

```python
# src/lee/orchestrator/execution/variable_resolver.py

import re
from typing import Dict, Any, Optional
from lee.orchestrator.ir.models import VariableIR

class VariableResolver:
    """变量引用解析器"""

    # 变量引用正则表达式
    VAR_PATTERN = re.compile(r'\$([a-zA-Z_][a-zA-Z0-9_.]*(?:\[.*?\])?)')
    STEP_OUTPUT_PATTERN = re.compile(r'\$s(\d+)_(\d+)(?:_(.+))?')

    def __init__(self):
        self.variables: Dict[str, Any] = {}

    def resolve_reference(self, reference: str, context: Dict[str, Any]) -> Any:
        """
        解析变量引用

        Args:
            reference: 变量引用字符串，如 "$inputs.prd" 或 "$s2_1.output"
            context: 上下文数据

        Returns:
            解析后的值
        """
        # 解析引用
        var_ir = self.parse_reference(reference)

        # 根据类型获取值
        if var_ir.source_type == "inputs":
            return self._get_from_inputs(var_ir.path, context.get("inputs", {}))
        elif var_ir.source_type == "step":
            return self._get_from_step(var_ir, context)
        elif var_ir.source_type == "context":
            return self._get_from_context(var_ir.path, context)

        raise ValueError(f"Unknown variable source type: {var_ir.source_type}")

    def parse_reference(self, reference: str) -> VariableIR:
        """解析变量引用字符串为 VariableIR"""
        if not reference.startswith("$"):
            raise ValueError(f"Invalid variable reference: {reference}")

        ref_without_dollar = reference[1:]

        # 检查是否是步骤输出引用
        step_match = self.STEP_OUTPUT_PATTERN.match(ref_without_dollar)
        if step_match:
            stage_num = step_match.group(1)
            step_num = step_match.group(2)
            output_name = step_match.group(3) or "output"
            step_id = f"s{stage_num}_{step_num}"

            return VariableIR(
                reference=reference,
                source_type="step",
                path=[output_name] if output_name else [],
                step_id=step_id,
            )

        # 检查是否是 inputs 引用
        if ref_without_dollar.startswith("inputs."):
            path = ref_without_dollar[len("inputs."):].split(".")
            return VariableIR(
                reference=reference,
                source_type="inputs",
                path=path,
            )

        # 默认为 context 引用
        path = ref_without_dollar.split(".")
        return VariableIR(
            reference=reference,
            source_type="context",
            path=path,
        )

    def _get_from_inputs(self, path: list, inputs: Dict[str, Any]) -> Any:
        """从 inputs 获取值"""
        value = inputs
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                raise ValueError(f"Cannot access key '{key}' on non-dict value")

        return value

    def _get_from_step(self, var_ir: VariableIR, context: Dict[str, Any]) -> Any:
        """从步骤输出获取值"""
        step_outputs = context.get("step_outputs", {})
        step_output = step_outputs.get(var_ir.step_id, {})

        value = step_output
        for key in var_ir.path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                raise ValueError(f"Cannot access key '{key}' on non-dict value")

        return value

    def _get_from_context(self, path: list, context: Dict[str, Any]) -> Any:
        """从上下文获取值"""
        value = context
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                raise ValueError(f"Cannot access key '{key}' on non-dict value")

        return value

    def resolve_all_in_dict(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """递归解析字典中的所有变量引用"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                if value.startswith("$"):
                    result[key] = self.resolve_reference(value, context)
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.resolve_all_in_dict(value, context)
            elif isinstance(value, list):
                result[key] = [self.resolve_all_in_dict(item, context) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value

        return result
```

---

### 3. 状态机执行方案

#### 3.1 扩展 WorkflowStateMachine

```python
# src/lee/orchestrator/execution/state_machine_v2.py

from typing import List, Dict, Any, Optional
from lee.orchestrator.ir.models import StateMachineIR, StateTransitionIR
from lee.orchestrator.storage.models import WorkflowStatus

class WorkflowStateMachineV2:
    """增强的工作流状态机（支持 spec-global 状态机）"""

    def __init__(self, store, state_machine_ir: Optional[StateMachineIR] = None):
        self.store = store
        self.state_machine_ir = state_machine_ir

    async def get_current_state(self, workflow_id: str) -> str:
        """获取当前状态"""
        instance = await self.store.get_workflow(workflow_id)
        return instance.data.get("current_state", "INIT")

    async def set_state(self, workflow_id: str, new_state: str) -> None:
        """设置新状态"""
        instance = await self.store.get_workflow(workflow_id)
        instance.data["current_state"] = new_state
        await self.store.update_workflow_data(workflow_id, instance.data)

    async def transition(self, workflow_id: str, trigger: str) -> Optional[str]:
        """
        执行状态转换

        Args:
            workflow_id: 工作流 ID
            trigger: 触发事件

        Returns:
            新状态，如果没有转换则返回 None
        """
        if not self.state_machine_ir:
            # 没有状态机定义，使用默认逻辑
            return None

        current_state = await self.get_current_state(workflow_id)
        next_states = self.state_machine_ir.get_next_states(current_state, trigger)

        if next_states:
            new_state = next_states[0]  # 取第一个可能的转换
            await self.set_state(workflow_id, new_state)

            # 更新 WorkflowStatus
            if new_state == "COMPLETED":
                await self.store.update_workflow_status(workflow_id, WorkflowStatus.COMPLETED)
            elif new_state == "BLOCKED":
                await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)

            return new_state

        return None
```

---

### 4. 门禁集成方案

#### 4.1 门禁执行器

```python
# src/lee/orchestrator/execution/gate_executor.py

from typing import Dict, Any, List, Tuple
from lee.orchestrator.ir.models import GateIR

class GateExecutor:
    """门禁规则执行器"""

    def __init__(self):
        self.gates: Dict[str, GateIR] = {}

    def register_gate(self, gate_id: str, gate_ir: GateIR) -> None:
        """注册门禁"""
        self.gates[gate_id] = gate_ir

    def evaluate_gate(self, gate_id: str, context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        评估门禁

        Args:
            gate_id: 门禁 ID
            context: 评估上下文

        Returns:
            (passed, issues): 通过标志和问题列表
        """
        if gate_id not in self.gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self.gates[gate_id]
        return gate.evaluate(context)

    def check_mandatory_criteria(self, gate_id: str, context: Dict[str, Any]) -> List[str]:
        """检查强制标准"""
        gate = self.gates.get(gate_id)
        if not gate:
            return []

        issues = []
        for rule in gate.mandatory_criteria:
            if not self._evaluate_rule(rule, context):
                issues.append(f"[BLOCKER] {rule.name}: {rule.error_message}")

        return issues

    def check_threshold_criteria(self, gate_id: str, context: Dict[str, Any]) -> List[str]:
        """检查阈值标准"""
        gate = self.gates.get(gate_id)
        if not gate:
            return []

        issues = []
        for rule in gate.threshold_criteria:
            if not self._evaluate_rule(rule, context):
                issues.append(f"[WARNING] {rule.name}: 未达到阈值")

        return issues

    def _evaluate_rule(self, rule: GateRuleIR, context: Dict[str, Any]) -> bool:
        """评估单个规则"""
        # TODO: 实现完整的表达式求值
        # 这里简化为总是返回 True
        return True
```

---

### 5. 集成到 TemplateManager

#### 5.1 修改 _parse_template_doc

```python
# 在 src/lee/orchestrator/execution/template_manager.py 中修改

from lee.orchestrator.execution.spec_global_parser import SpecGlobalParser
from lee.orchestrator.ir.converter import IRConverter

class TemplateManager:
    def __init__(self, template_dir: str = "specs/workflows"):
        self.template_dir = Path(template_dir)
        self._cache: Dict[str, WorkflowTemplate] = {}
        self.spec_global_parser = SpecGlobalParser()
        self.ir_converter = IRConverter()

    def _parse_template_doc(self, doc: Dict[str, Any], template_id: str) -> WorkflowTemplate:
        """解析模板文档（支持 spec-global 格式）"""
        kind = doc.get("kind", "")

        if kind == "workflow":
            # 使用 spec-global 解析器
            workflow_ir = self.spec_global_parser.parse_workflow(doc)

            # 转换为 WorkflowTemplate
            template = self.ir_converter.ir_to_template(workflow_ir)

            # 缓存 IR 以便后续使用
            template.config["_ir"] = workflow_ir

            return template
        else:
            # 使用原有逻辑
            # ...（保持原有代码不变）
```

---

## 🧪 测试验证计划

### 1. 单元测试

#### 1.1 IR 模型测试

```python
# tests/test_ir_models.py

import pytest
from lee.orchestrator.ir.models import *

def test_variable_ir_parsing():
    """测试 VariableIR 解析"""
    resolver = VariableResolver()

    # 测试 inputs 引用
    var_ir = resolver.parse_reference("$inputs.prd")
    assert var_ir.source_type == "inputs"
    assert var_ir.path == ["prd"]

    # 测试步骤输出引用
    var_ir = resolver.parse_reference("$s2_1.output")
    assert var_ir.source_type == "step"
    assert var_ir.step_id == "s2_1"

def test_gate_evaluation():
    """测试门禁评估"""
    gate = GateIR(
        gate_id="test_gate",
        name="Test Gate",
        description="",
        mandatory_criteria=[
            GateRuleIR(
                rule_id="C001",
                name="Test Rule",
                rule_type="mandatory",
                rule_expression="true",
                severity="blocker",
                exemption_allowed=False,
            )
        ],
        threshold_criteria=[],
        risk_acceptance_criteria=[],
        exemption_policy={},
        signoff_requirements={},
    )

    passed, issues = gate.evaluate({})
    assert len(issues) == 1
```

#### 1.2 解析器测试

```python
# tests/test_spec_global_parser.py

import pytest
from lee.orchestrator.execution.spec_global_parser import SpecGlobalParser

def test_parse_qa_workflow():
    """测试解析 QA 工作流"""
    parser = SpecGlobalParser()
    workflow_ir = parser.parse_workflow_file("spec-global/departments/qa/workflows/test-case-design-pipeline/v1/workflow.yaml")

    assert workflow_ir.id == "workflow.qa.test_case_design_pipeline"
    assert len(workflow_ir.inputs) == 4
    assert len(workflow_ir.outputs) == 3
    assert len(workflow_ir.state_machine.states) == 11

def test_parse_gate_file():
    """测试解析门禁文件"""
    parser = SpecGlobalParser()
    gate_ir = parser.parse_gate_file("spec-global/departments/qa/gates/design-input-gate/v1/gate.yaml")

    assert gate_ir.gate_id == "gate.qa.design_input_gate"
    assert len(gate_ir.mandatory_criteria) == 5
```

---

### 2. 集成测试

#### 2.1 端到端工作流执行

```python
# tests/test_e2e_workflow_execution.py

import pytest
from lee.orchestrator.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_qa_workflow_execution():
    """测试 QA 工作流端到端执行"""
    orchestrator = Orchestrator(store=SQLiteStore(":memory:"))

    # 创建工作流实例
    instance = await orchestrator.create_workflow(
        level=WorkflowLevel.DEPARTMENT,
        template_id="workflow.qa.test_case_design_pipeline",
        data={
            "inputs": {
                "prd": "...",
                "technical_architecture": "...",
                "ui_prototype": "...",
                "ui_page": "...",
            }
        }
    )

    # 执行到第一个门禁
    result = await orchestrator.run_until_blocked(instance.id)

    # 验证状态
    state = await orchestrator.get_state(instance.id)
    assert state.current_step == "s1_1_validate_inputs"
```

---

### 3. 真实项目验证

#### 3.1 已有项目迁移测试

1. **选择测试项目**
   - 选择 1-2 个正在使用 Orchestrator 的项目
   - 确保项目覆盖不同场景（简单/复杂工作流）

2. **迁移步骤**
   - 将现有工作流转换为 spec-global 格式
   - 验证执行结果一致性
   - 测试所有边界情况

3. **验证标准**
   - 功能一致性：执行结果完全相同
   - 性能一致性：执行时间无显著增加
   - 可维护性：代码结构更清晰

---

## ❓ 需要确认的问题清单

### 架构决策

1. **IR 结构范围**
   - [ ] IR 是否需要支持完整的 spec-global 语义？
   - [ ] 还是只需要支持 Orchestrator 需要的子集？

2. **向后兼容边界**
   - [ ] 是否需要支持旧的 `level` 字段？
   - [ ] 是否需要支持旧的步骤格式？

3. **执行模型选择**
   - [ ] 单一执行者切换提示词（prompt_switch）？
   - [ ] 还是多进程/多 Agent 执行？

### 性能考虑

4. **解析性能**
   - [ ] 是否需要缓存解析结果？
   - [ ] 缓存失效策略是什么？

5. **执行性能**
   - [ ] 变量解析是否会影响性能？
   - [ ] 是否需要预处理步骤依赖图？

### 功能范围

6. **表达式引擎**
   - [ ] 需要多强大的表达式求值能力？
   - [ ] 是否需要支持自定义函数？

7. **门禁规则**
   - [ ] 是否需要支持动态规则（运行时生成）？
   - [ ] 是否需要支持规则组合（AND/OR）？

### 工具和调试

8. **可视化需求**
   - [ ] 是否需要工作流可视化工具？
   - [ ] 是否需要状态机调试工具？

9. **错误处理**
   - [ ] 解析错误的粒度要求？
   - [ ] 是否需要提供修复建议？

---

## 📊 进度跟踪

### P0 进度

| 阶段 | 任务 | 状态 | 负责人 | 截止日期 |
|------|------|------|--------|---------|
| P0.1 | IR 结构设计 | 🚧 进行中 | - | 2026-02-05 |
| P0.2 | YAML 解析器 | 📋 计划中 | - | 2026-02-06 |
| P0.3 | 变量解析器 | 📋 计划中 | - | 2026-02-06 |
| P0.4 | 基础集成 | 📋 计划中 | - | 2026-02-07 |

### P1 进度

| 阶段 | 任务 | 状态 | 负责人 | 截止日期 |
|------|------|------|--------|---------|
| P1.1 | 状态机执行引擎 | 📋 计划中 | - | 2026-02-10 |
| P1.2 | 门禁规则引擎 | 📋 计划中 | - | 2026-02-14 |
| P1.3 | 条件执行支持 | 📋 计划中 | - | 2026-02-16 |
| P1.4 | 人类审批增强 | 📋 计划中 | - | 2026-02-19 |

---

## 📚 参考文档

### 相关规范

- [spec-global 目录结构](E:\ai\LEE\spec-global)
- [QA 工作流示例](E:\ai\LEE\spec-global\departments\qa\workflows\test-case-design-pipeline\v1\workflow.yaml)
- [门禁规则示例](E:\ai\LEE\spec-global\departments\qa\gates\design-input-gate\v1\gate.yaml)
- [Orchestrator 代码](E:\ai\LEE\src\lee\orchestrator)

### 技术文档

- [Orchestrator 集成指南](E:\ai\LEE\spec-global\departments\devops\docs\orchestrator-integration.md)

---

## 🔄 版本历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-02-05 | 初始版本 | LEE Core Team |

---

**文档状态**: 🚧 实施中
**最后更新**: 2026-02-05
**下次审查**: 2026-02-07
