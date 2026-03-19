---
id: TECH-FEAT-SRC-046-005
ssot_type: tech
title: Fitness L3 工作流实现技术设计
status: draft
version: v1
workflow_instance_id: wf_task_296dfcdf
parent_id: FEAT-SRC-046-005
derived_from_ids:
- id: FEAT-SRC-046-005
  version: v1
  required: true
source_refs:
- ADR-024#11-rollout
- ADR-024#8-integration-decision
owner: null
tags: [governance, fitness, l3-workflow, technical-design]
properties:
  contract_key: tech
  identity_kind: ssot
---

# Fitness L3 工作流实现技术设计

## 1. 架构概述

### 1.1 设计目标

实现 Fitness L3 工作流模板，嵌入 Product/Dev/QA L2 工作流的关键决策点前，提供统一的完成条件验证能力。

**核心原则**：
- **单 L3 模板多嵌入点**：统一模板，按需加载规则
- **规则与执行分离**：Fitness Rule 独立声明，Fitness Runner 统一执行
- **结果标准化**：fitness_result 结构统一，可被 gate/supervisor 直接消费

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                   L2 Workflow Embedding                 │
│  Product L2 │ Dev L2 │ QA L2                            │
│     │            │           │                          │
│     └────────────┴───────────┘                          │
│                  │                                      │
│                  ▼                                      │
├─────────────────────────────────────────────────────────┤
│              Fitness L3 Template                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Phases: rule_load → rule_execution →            │    │
│  │           result_aggregate → gate_integration   │    │
│  └─────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────┤
│              Fitness Runner                             │
│  - Rule Loader (按需加载适用规则)                       │
│  - Rule Executor (执行 rule 并收集结果)                 │
│  - Result Aggregator (聚合 fitness_result)              │
│  - Gate Integrator (推送结果到 Gate)                    │
├─────────────────────────────────────────────────────────┤
│              Fitness Rule Schema                        │
│  spec/fitness/rules/                                    │
│  - FCR-001 ~ FCR-005 (5 个 P0 Dimension 规则)           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 核心模块设计

### 2.1 Fitness L3 工作流模板

**文件位置**: `spec-global/departments/governance/workflows/templates/fitness-l3-template.yaml`

** phases 设计**:

```yaml
phases:
  - id: rule_load
    name: "Load Fitness Rules"
    description: "从 spec/fitness/ 加载适用规则"
    default_complexity: S
    steps:
      - id: load_rules
        agent: agent.governance.fitness_loader
        config:
          embedding_point: "{{ params.embedding_point }}"
          subject_refs: "{{ params.subject_refs }}"
          rule_directory: "spec/fitness/rules/"

  - id: rule_execution
    name: "Execute Fitness Rules"
    description: "执行 fitness rule 并收集结果"
    default_complexity: L
    depends_on: [rule_load]
    spawns_l3: false
    steps:
      - id: execute_rules
        agent: agent.governance.fitness_runner
        config:
          rules: "{{ steps.rule_load.output.rules }}"
          subject_refs: "{{ params.subject_refs }}"
          workspace: "{{ params.workspace }}"

  - id: result_aggregate
    name: "Aggregate Fitness Result"
    description: "聚合 fitness_result 对象"
    default_complexity: S
    depends_on: [rule_execution]
    steps:
      - id: aggregate
        agent: agent.governance.result_aggregator
        config:
          dimension_results: "{{ steps.rule_execution.output.dimension_results }}"
          hard_gate_results: "{{ steps.rule_execution.output.hard_gate_results }}"

  - id: gate_integration
    name: "Gate Integration"
    description: "将 fitness_result 推送到 Gate"
    default_complexity: S
    depends_on: [result_aggregate]
    steps:
      - id: push_to_gate
        agent: agent.governance.gate_integration
        config:
          fitness_result: "{{ steps.result_aggregate.output.fitness_result }}"
          gate_id: "{{ params.gate_id }}"
```

**输出对象 (outputs)**:

```yaml
outputs:
  - path: "{{ fitness_output_dir }}/fitness_result_{{ subject_refs | join('_') }}.json"
    type: file
    format: json
    description: "Fitness Result 结构化输出"
    required: true

  - path: "{{ fitness_output_dir }}/fitness_report_{{ subject_refs | join('_') }}.md"
    type: file
    format: markdown
    description: "Fitness Report 人读视图"
    required: false
```

### 2.2 Fitness Rule Schema

**文件位置**: `spec/fitness/rules/`

**Schema 结构**:

```yaml
# spec/fitness/rules/FCR-001__contract-parity.yaml
rule_id: FCR-001
dimension: contract_consistency
rule_class: hard_gate  # hard_gate | quality_signal
severity: blocker  # blocker | critical | warning | info
description: "Contract parity check - 实现与冻结合同一致"

execution_method:
  type: contract_diff
  config:
    frozen_contract_path: "spec/contracts/{{ contract_id }}.yaml"
    implementation_path: "{{ params.workspace }}/src/"
    diff_tool: "yaml-diff"

evidence_binding:
  type: git_diff_against_frozen_contract
  config:
    base_ref: "frozen_contract_{{ contract_id }}"
    head_ref: "HEAD"

success_criteria:
  - "所有 API 端点与冻结合同一致"
  - "请求/响应字段无遗漏无多余"
  - "数据类型和约束匹配合同定义"

failure_message: "实现与冻结合同存在差异，请修复或更新合同"
```

**5 个 P0 规则最小集**:

| Rule ID | Dimension | Rule Class | Severity | Description |
|---------|-----------|------------|----------|-------------|
| FCR-001 | contract_consistency | hard_gate | blocker | Contract parity check |
| FCR-002 | testability | hard_gate | blocker | Unit/Integration/Smoke 必要验证 |
| FCR-003 | integration_closure | hard_gate | critical | 跨模块集成契约验证 |
| FCR-004 | evidence_completeness | hard_gate | blocker | 证据包完整性检查 |
| FCR-005 | path_governance | hard_gate | blocker | Canonical/Forbidden 路径检查 |

### 2.3 Fitness Runner 执行器

**文件位置**: `src/lee/governance/fitness_runner.py`

**核心类设计**:

```python
class FitnessRunner:
    """Fitness Rule 执行器"""

    def __init__(self, workspace: str, subject_refs: List[str]):
        self.workspace = workspace
        self.subject_refs = subject_refs
        self.rules: List[FitnessRule] = []
        self.dimension_results: Dict[str, DimensionResult] = {}
        self.hard_gate_results: Dict[str, bool] = {}
        self.warnings: List[str] = []
        self.command_runs: List[CommandRun] = []
        self.evidence_refs: List[str] = []

    def load_rules(self, embedding_point: str) -> List[FitnessRule]:
        """根据嵌入点和 subject_refs 加载适用规则"""
        # 从 spec/fitness/rules/ 加载 YAML 规则文件
        # 根据 embedding_point 过滤 (product/dev/qa)
        # 根据 subject_refs 过滤 (FEAT/TASK/TESTPLAN)
        pass

    def execute(self) -> FitnessResult:
        """执行所有加载的规则并聚合结果"""
        for rule in self.rules:
            result = self._execute_rule(rule)
            self._aggregate_result(rule, result)

        return self._build_fitness_result()

    def _execute_rule(self, rule: FitnessRule) -> RuleExecutionResult:
        """执行单条规则"""
        # 根据 execution_method.type 调度执行器
        # 收集 evidence_binding
        # 判定 success_criteria
        pass

    def _build_fitness_result(self) -> FitnessResult:
        """构建 fitness_result 对象"""
        final_status = self._compute_final_status()
        return FitnessResult(
            subject_refs=self.subject_refs,
            dimension_results=self.dimension_results,
            hard_gate_results=self.hard_gate_results,
            warnings=self.warnings,
            command_runs=self.command_runs,
            evidence_refs=self.evidence_refs,
            summary=self._build_summary(),
            final_status=final_status,
        )
```

**fitness_result 输出结构**:

```json
{
  "subject_refs": ["FEAT-SRC-046-001", "TASK-DEVPLAN-REL-1.4.0-001"],
  "dimension_results": {
    "contract_consistency": {
      "status": "pass",
      "rules_checked": 1,
      "rules_passed": 1,
      "details": {...}
    },
    "testability": {
      "status": "fail",
      "rules_checked": 1,
      "rules_passed": 0,
      "failure_reason": "Unit test coverage below 80%"
    },
    "integration_closure": { "status": "pass", ... },
    "evidence_completeness": { "status": "pass", ... },
    "path_governance": { "status": "pass", ... }
  },
  "hard_gate_results": {
    "FCR-001": true,
    "FCR-002": false,
    "FCR-003": true,
    "FCR-004": true,
    "FCR-005": true
  },
  "warnings": ["Coverage slightly below target (78% vs 80%)"],
  "command_runs": [
    {
      "command": "pytest --cov=src tests/",
      "exit_code": 0,
      "output_path": ".workflow/fitness/pytest_output.txt",
      "started_at": "2026-03-18T10:00:00Z",
      "completed_at": "2026-03-18T10:05:00Z"
    }
  ],
  "evidence_refs": [
    "evidence/pytest-coverage-report.json",
    "evidence/git-diff-against-contract.txt"
  ],
  "summary": "Fitness check failed: testability dimension (FCR-002). Unit test coverage 78% < 80% threshold.",
  "final_status": "fail"
}
```

### 2.4 嵌入点集成

#### Dev L2 嵌入点

**修改文件**: `spec-global/departments/dev/workflows/templates/feature-l2-template.yaml`

**修改位置**: `smoke_test` phase 之前插入 Fitness L3

```yaml
phases:
  # ... existing phases ...

  - id: smoke_test
    name: "Smoke Test"
    description: "Smoke test gate - blocks merge on failure"
    default_complexity: S
    depends_on: [integration, fitness_check]  # 添加 fitness_check 依赖

  - id: fitness_check
    name: "Fitness Check"
    description: "Fitness L3 workflow - Smoke test prerequisite"
    default_complexity: L
    depends_on: [integration]
    spawns_l3: true
    l3_template_id: template.governance.fitness
    params:
      embedding_point: dev_l2
      subject_refs: ["{{ task_id }}"]
      gate_id: "smoke_gate"
      fitness_output_dir: ".workflow/fitness"
```

**Gate 消费集成**:

修改 `dev-smoke-l3-template.yaml`，在启动前检查 fitness_result：

```yaml
steps:
  - id: check_fitness_result
    agent: agent.governance.fitness_checker
    config:
      fitness_result_path: ".workflow/fitness/fitness_result_{{ task_id }}.json"
      require_status: "pass"
    on_failure:
      action: "block_and_report"
      message: "Fitness check failed. See fitness_result for details."
```

#### Product L2 嵌入点 (P1)

**修改文件**: `spec-global/departments/product/workflows/templates/feat-to-delivery-prep/v1/workflow.yaml`

在 `delivery_prep_freeze` 前插入 Fitness L3 验证。

#### QA L2 嵌入点 (P1)

**修改文件**: `spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml`

在 `test_report` phase 前插入 Fitness L3 验证。

---

## 3. 目录结构

```
spec/
├── fitness/
│   ├── rules/
│   │   ├── FCR-001__contract-parity.yaml
│   │   ├── FCR-002__test-verification.yaml
│   │   ├── FCR-003__integration-closure.yaml
│   │   ├── FCR-004__evidence-completeness.yaml
│   │   └── FCR-005__path-governance.yaml
│   └── schemas/
│       ├── fitness_rule_schema.yaml
│       └── fitness_result_schema.json

spec-global/departments/
├── governance/workflows/templates/
│   └── fitness-l3-template.yaml
├── dev/workflows/templates/
│   └── feature-l2-template.yaml (modified)
├── product/workflows/templates/
│   └── feat-to-delivery-prep/v1/workflow.yaml (modified - P1)
└── qa/workflows/templates/
    └── test-plan-l2-template.yaml (modified - P1)

src/lee/
└── governance/
    ├── __init__.py
    ├── fitness_runner.py
    ├── fitness_rule_loader.py
    ├── result_aggregator.py
    ├── gate_integrator.py
    └── agents/
        ├── __init__.py
        ├── fitness_loader.py
        ├── fitness_runner.py
        ├── result_aggregator.py
        └── gate_integrator.py
```

---

## 4. 验收标准

### 4.1 Fitness L3 模板验收

- [ ] 模板 YAML 语法正确，可通过 `lee workflow validate`
- [ ] 4 个 phases 定义完整 (rule_load, rule_execution, result_aggregate, gate_integration)
- [ ] outputs 定义符合 ADR-024 fitness_result 结构

### 4.2 Fitness Rule 验收

- [ ] 5 个 P0 规则文件存在且语法正确
- [ ] 每条规则包含必需的 8 个字段
- [ ] execution_method 可实际执行

### 4.3 Fitness Runner 验收

- [ ] FitnessRunner 类可实现加载/执行/聚合全流程
- [ ] fitness_result 输出 JSON 符合 schema
- [ ] command_runs 可追溯实际执行的命令

### 4.4 嵌入点验收 (P0)

- [ ] Dev L2 可正确调用 Fitness L3
- [ ] fitness_result=fail 可阻断 smoke_test
- [ ] Gate 可消费 fitness_result

---

## 5. 依赖与约束

### 5.1 技术依赖

- Python 3.10+
- PyYAML (规则文件解析)
- jsonschema (fitness_result 校验)

### 5.2 治理依赖

- ADR-024 必须为 frozen 状态
- Fitness Rule Schema 需通过 SSOT 验证

### 5.3 约束条件

- 不影响现有 Gate/Approval/Supervisor 职责边界
- fitness_result 不直接等同于 workflow completion
- 仅 P0 切片 (Dev L2 嵌入) 为必选，Product/QA 嵌入为 P1

---

## 6. 迁移路径

### Phase A (P0 - 当前)

1. 创建 Fitness L3 模板
2. 创建 5 个 P0 Fitness Rule
3. 实现 Fitness Runner 最小集
4. 嵌入 Dev L2 (Smoke 前置)
5. ADR-024 提升为 frozen

### Phase B (P1)

1. 嵌入 Product L2 (FEAT 冻结验证)
2. 嵌入 QA L2 (证据完整性验证)
3. CLI 集成 (`lee fitness-run`)
4. 扩展 Dimensions 和 Rules

### Phase C (未来)

1. RELEASE L1 工作流实现后迁移
2. 更多 workflow 默认依赖 fitness_result
3. 高风险主链启用 fail fast
