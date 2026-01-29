# Spec-Global → v3.1 映射对照表

> **目的**: 详细展示 Spec-Global 各字段到 v3.1 Orchestrator 的映射关系
> **版本**: 1.0
> **更新日期**: 2026-01-28
> **适用对象**: WorkflowLoader / AgentLoader / ContractLoader 实现者

---

## 一、Workflow 映射对照表

### 1.1 顶层元数据映射

| Spec-Global 字段 | v3.1 目标 | 映射规则 | 注意事项 |
|-----------------|-----------|---------|---------|
| `kind: workflow` | `WorkflowTemplate.kind` | 直接映射 | 固定值 "workflow" |
| `id` | `WorkflowTemplate.id` | 直接映射 | 唯一标识符 |
| `version` | `WorkflowTemplate.version` | 直接映射 | 版本号 |
| `name` | `WorkflowTemplate.name` | 直接映射 | 显示名称 |
| `description` | `WorkflowTemplate.description` | 直接映射 | 描述信息 |
| `tags` | `WorkflowTemplate.tags` | 直接映射 | 标签数组 |
| `owner` | `WorkflowTemplate.metadata.owner` | 移至 metadata | 用于权限控制 |
| `inputs_contract` | `WorkflowTemplate.input_contract` | 直接映射 | 输入契约引用 |
| `outputs_contract` | `WorkflowTemplate.output_contract` | 直接映射 | 输出契约引用 |
| `_metadata.yaml.level` | `WorkflowTemplate.metadata.level` | 从注册表读取 | 默认层级 |
| `_metadata.yaml.notes` | `WorkflowTemplate.metadata.notes` | 从注册表读取 | 备注信息 |

### 1.2 Orchestration 配置映射

| Spec-Global 字段 | v3.1 目标 | 映射规则 | ⚠️ 注意事项 |
|-----------------|-----------|---------|------------|
| `orchestration.type: dag` | ⚠️ **暂不支持** | v3.1 初期只支持线性执行 | DAG 编排需要 Phase 2 |
| `orchestration.timeout_ms` | `WorkflowTemplate.timeout_ms` | 直接映射 | 超时时间 |
| `orchestration.parallel_phases` | ⚠️ **部分支持** | v3.1 通过 spawn 实现 | 并行 Phase 通过子 workflow 实现 |

### 1.3 Stages → Steps 扁平化映射

#### 1.3.1 基本映射规则

```yaml
# Spec-Global (嵌套结构)
stages:
  - id: s3_0_project_init
    steps:
      - id: s3_0_1_project_setup
        run: agent.dev.tech_lead
        dependencies:
          requires: []
        inputs: [...]
        outputs: [...]
        on_error: {...}

# v3.1 (扁平结构)
steps:
  - id: s3_0_1_project_setup
    name: "项目配置初始化"
    stage_id: "s3_0_project_init"  # 保留 stage 信息
    executor_type: "llm"
    agent_id: "agent.dev.tech_lead"
    dependencies: []
    inputs: [...]
    outputs: [...]
    on_error: {...}
```

#### 1.3.2 Step 字段详细映射

| Spec-Global 字段 | v3.1 StepTemplate 字段 | 映射规则 | 代码示例 |
|-----------------|----------------------|---------|---------|
| `id` | `id` | 直接映射 | `s3_0_1_project_setup` |
| `name` | `name` | 直接映射 | `项目配置初始化` |
| `description` | `description` | 直接映射 | 技术方案撰写 |
| `stage.id` | `stage_id` | 新增：保留 stage 信息 | `s3_0_project_init` |
| `run` (agent) | `agent_id` + `executor_type=llm` | 解析 agent 引用 | `agent.dev.tech_lead` → agent_id="agent.dev.tech_lead", executor_type="llm" |
| `run` (skill) | `skill_id` + `executor_type` | 解析 skill 引用 | `skill.ci.run_unit_tests` → skill_id="skill.ci.run_unit_tests", executor_type="shell" |
| `type: human_decision` | `executor_type=human` | 特殊类型处理 | human_gate |
| `dependencies.requires` | `dependencies` | 直接映射（数组） | `["s3_0_1_project_setup"]` |
| `dependencies.parallel_with` | ⚠️ **暂不支持** | WARN + 串行化 | 记录警告，按串行执行 |
| `inputs` | `inputs` | 直接映射（字典） | `{"prd": "$inputs.prd"}` |
| `outputs` | `outputs` | 直接映射（数组） | `[{"path": "project.yaml", "contract": "..."}]` |
| `outputs[].contract` | `output_contract` | 提取契约引用 | `contract.dev.project_config_contract` |
| `outputs[].freeze` | ⚠️ **语义转换** | 转为 artifact metadata | `freeze: true` → `metadata.freeze: true` |
| `output_validation.validation_mode` | `validation_mode` | 直接映射 | `strict` / `warn` / `skip` |
| `output_validation.on_failure.action` | `on_failure.action` | 直接映射 | `retry` / `block` / `warn` |
| `on_error.action` | `on_error.action` | 直接映射 | `fail` / `skip` / `escalate` |
| `on_error.max_retries` | `on_error.max_retries` | 直接映射 | `3` |
| `human_gate` | `gates[]` | 转为 gate 引用 | `h1_plan_review` → gates: ["gate.dev.h1_plan_review"] |
| `execution.model` | `execution_model` | 直接映射 | `prompt_switch` |
| `execution.timeout` | `timeout_ms` | 单位转换 | `60m` → `3600000` (ms) |

### 1.4 条件字段映射（⚠️ 语义损失风险）

| Spec-Global 字段 | v3.1 处理方式 | ⚠️ 风险 | 对策 |
|-----------------|---------------|---------|------|
| `condition` | ⚠️ **WARN** | 条件分支逻辑可能丢失 | 记录警告，建议人工检查 |
| `parallel: true` | ⚠️ **WARN + 串行化** | 并行语义丢失 | 记录警告，按依赖顺序串行 |
| `for_each` | ❌ **FAIL FAST** | 不支持循环执行 | 提示用户手动展开或由 Agent 处理 |
| `triggered_by` | ❌ **FAIL FAST** | 不支持触发式执行 | 提示用户改用 spawn + 依赖 |
| `mode: continuous` | ⚠️ **WARN** | 持续模式语义丢失 | 记录警告，转为单次执行 |

---

## 二、Gate 映射对照表

### 2.1 human_in_the_loop → Gate 映射

```yaml
# Spec-Global
human_in_the_loop:
  - id: h1_plan_review
    purpose: "审批研发计划"
    gate:
      enabled: true
      type: approval
      blocking: true
      timeout:
        duration: 48h
        action: escalate
      approval:
        required_roles: [product_owner, tech_lead]
        min_approvals: 1
    inputs_to_review: [...]
    review_checklist: [...]
    actions:
      approve: {...}
      adjust: {...}
      reject: {...}

# v3.1 WorkflowTemplate.gates[]
gates:
  - id: gate.dev.h1_plan_review
    step_id: s3_1_2_plan_approval  # 绑定到哪个 step
    type: approval
    blocking: true
    timeout_ms: 172800000  # 48h
    required_roles: [product_owner, tech_lead]
    min_approvals: 1
    inputs_to_review: [...]
    review_checklist: [...]
    actions:
      - action: approve
        label: "批准计划，启动调度执行"
        next_step: continue
      - action: adjust
        label: "调整计划后重新提交"
        next_step: retry_step
      - action: reject
        label: "否决计划，需重新规划"
        next_step: fail
```

### 2.2 Gate 字段详细映射

| Spec-Global 字段 | v3.1 Gate 字段 | 映射规则 | 代码示例 |
|-----------------|--------------|---------|---------|
| `id` | `id` | 添加前缀 `gate.{dept}.` | `h1_plan_review` → `gate.dev.h1_plan_review` |
| `purpose` | `purpose` | 直接映射 | "审批研发计划" |
| `gate.type` | `type` | 直接映射 | `approval` / `review` / `decision` |
| `gate.blocking` | `blocking` | 直接映射 | `true` / `false` |
| `gate.timeout.duration` | `timeout_ms` | 单位转换 | `48h` → `172800000` (ms) |
| `gate.timeout.action` | `timeout_action` | 直接映射 | `escalate` / `skip` / `fail` |
| `gate.approval.required_roles` | `required_roles` | 直接映射 | `[product_owner, tech_lead]` |
| `gate.approval.min_approvals` | `min_approvals` | 直接映射 | `1` |
| `inputs_to_review` | `inputs_to_review` | 直接映射 | `["03-planning/development-plan.yaml"]` |
| `review_checklist` | `checklist` | 直接映射 | `["Phase 划分是否合理"]` |
| `actions` | `actions` | 转为数组 | 见上方代码示例 |

### 2.3 Gate 类型映射

| Spec-Global 类型 | v3.1 类型 | 处理方式 |
|-----------------|-----------|---------|
| `approval` | `approval` | 需要显式审批，才能继续 |
| `review` | `review` | 需要审查，可以带条件通过 |
| `decision` | `decision` | 需要决策，可选择不同分支 |

---

## 三、Agent 映射对照表

### 3.1 agent_resources → Agent 模型映射

```yaml
# Spec-Global
agent_resources:
  decision_layer:
    - id: agent.dev.tech_lead
      name: Tech Lead
      spec: ../../agents/tech-lead/v1/agent.yaml
      responsibility: "架构决策 + ADR 机制"
      execution_model:
        type: prompt_switch
        config:
          persona_file: ../../agents/tech-lead/v1/persona.md

# v3.1 Agent 模型（统一模型）
Agent(
  id="agent.dev.tech_lead",
  name="Tech Lead",
  spec_path="departments/dev/agents/tech-lead/v1/agent.yaml",
  capabilities=["架构决策", "ADR 机制"],
  execution_model=ExecutionModel(
    type="prompt_switch",
    config={"persona_file": "..."}
  ),
  input_contract="contracts/...",
  output_contract="contracts/adr-output/v1/schema.json"
)
```

### 3.2 Agent 字段详细映射

| Spec-Global 字段 | v3.1 Agent 字段 | 映射规则 | 代码示例 |
|-----------------|-----------------|---------|---------|
| `id` | `id` | 直接映射 | `agent.dev.tech_lead` |
| `name` | `name` | 直接映射 | `Tech Lead` |
| `spec` | `spec_path` | 转为相对路径 | `../../agents/tech-lead/v1/agent.yaml` → `spec_global/departments/dev/agents/tech-lead/v1/agent.yaml` |
| `responsibility` | `capabilities` | 转为数组 | `"架构决策 + ADR 机制"` → `["架构决策", "ADR 机制"]` |
| `execution_model.type` | `execution_model.type` | 直接映射 | `prompt_switch` |
| `execution_model.config` | `execution_model.config` | 直接映射 | `{"persona_file": "..."}` |
| `output_contract` | `output_contract` | 直接映射 | `contracts/adr-output/v1/schema.json` |
| `hard_boundary` | `constraints.hard_boundary` | 移至 constraints | `"只负责测试设计"` |
| `invoked_by` | `constraints.invoked_by` | 移至 constraints | `tech_lead` |

### 3.3 Step.run 解析映射

| Spec-Global run 格式 | v3.1 executor_type | v3.1 agent_id/skill_id | 解析逻辑 |
|---------------------|-------------------|---------------------|---------|
| `agent.dev.tech_lead` | `llm` | `agent.dev.tech_lead` | 以 `agent.` 开头 → llm executor |
| `skill.ci.run_unit_tests` | `shell` | `skill.ci.run_unit_tests` | 以 `skill.` 开头 → shell executor |
| `type: human_decision` | `human` | `null` | 特殊类型 → human executor |
| `bash: "echo hello"` | `shell` | `null` | 包含 bash/shell → shell executor |

---

## 四、Contract 映射对照表

### 4.1 Contract 加载映射

```yaml
# Spec-Global workflow 中的引用
outputs:
  - path: "03-planning/development-plan.yaml"
    contract: ../../contracts/development-plan-contract/v1/schema.json

# v3.1 ContractLoader 处理
contract_id = "contract.dev.development_plan_contract"
contract_schema = loader.load_contract("departments/dev/contracts/development-plan-contract/v1/schema.json")
```

### 4.2 Contract 路径解析映射

| Spec-Global 路径 | v3.1 contract_id | 解析规则 |
|-----------------|-----------------|---------|
| `../../contracts/plan-contract/v1/schema.yaml` | `contract.core.plan_contract` | 相对路径 + 类型转换 |
| `../../contracts/development-plan-contract/v1/schema.json` | `contract.dev.development_plan_contract` | 部门前缀 + contract 名称 |
| `contracts/test-case-contract/v1/schema.json` | `contract.dev.test_case_contract` | 缺省 `../../` 时从部门 contracts 查找 |

### 4.3 Contract 验证语义映射

| Spec-Global 验证配置 | v3.1 验证行为 | 状态语义 |
|---------------------|-------------|---------|
| `output_validation.validation_mode: strict` | SchemaValidator 严格验证 | 验证失败 → StepResult(failed) → WorkflowStatus.BLOCKED |
| `output_validation.validation_mode: warn` | SchemaValidator 警告模式 | 验证失败 → StepResult(success) + warnings |
| `output_validation.validation_mode: skip` | 跳过验证 | StepResult(success) |
| `output_validation.on_failure.action: block` | 阻塞性失败 | WorkflowStatus.FAILED |
| `output_validation.on_failure.action: retry` | 可重试失败 | 重试逻辑（由 StateMachine 处理） |
| `output_validation.on_failure.max_retries: 2` | 最大重试次数 | 最多重试 2 次 |

---

## 五、条件门禁映射对照表

### 5.1 conditional_human_gate 映射

```yaml
# Spec-Global
conditional_human_gate:
  gate_id: h4_code_review
  trigger_conditions:
    - condition: "critical_issues > 0"
      reason: "发现 Critical 级别问题，需要人类确认"
    - condition: "code_quality_score < 6"
      reason: "代码质量评分过低"
  auto_approve_conditions:
    - "critical_issues == 0"
    - "code_quality_score >= 7"

# v3.1 (Gate + 条件判断)
gates:
  - id: gate.phase.h4_code_review
    type: review
    blocking: false
    trigger_mode: agent_driven
    trigger_conditions:
      - field: "critical_issues"
        operator: ">"
        value: 0
        trigger_gate: true
        reason: "发现 Critical 级别问题，需要人类确认"
      - field: "code_quality_score"
        operator: "<"
        value: 6
        trigger_gate: true
        reason: "代码质量评分过低"
    auto_approve_conditions:
      - field: "critical_issues"
        operator: "=="
        value: 0
      - field: "code_quality_score"
        operator: ">="
        value: 7
```

### 5.2 条件表达式映射

| Spec-Global 表达式 | v3.1 解析 | ⚠️ 注意 |
|-------------------|----------|-------|
| `critical_issues > 0` | 字段比较 | 需要在 Step 输出中包含该字段 |
| `code_quality_score < 6` | 数值比较 | 需要字段类型为数字 |
| `has_database_changes` | 布尔字段 | 需要字段类型为 boolean |

---

## 六、 Enforcement 映射对照表

### 6.1 enforcement 规则映射

```yaml
# Spec-Global
enforcement:
  skip_prevention:
    enabled: true
    rule: "NO_SKIP_ALLOWED"
    violation_action: "FAIL_FAST"
  completion_validation:
    enabled: true
    require_outputs: true
    require_quality_gate: true

# v3.1 (WorkflowTemplate.enforcement)
enforcement:
  skip_allowed: false
  require_outputs: true
  quality_gate_required: true
  violation_action: "fail_fast"
```

| Spec-Global enforcement | v3.1 enforcement | 映射规则 |
|-------------------------|------------------|---------|
| `skip_prevention.enabled: true` | `skip_allowed: false` | 取反映射 |
| `rule: "NO_SKIP_ALLOWED"` | (记录到 metadata) | 信息保留 |
| `violation_action: "FAIL_FAST"` | `violation_action: "fail_fast"` | 直接映射 |
| `completion_validation.require_outputs: true` | `require_outputs: true` | 直接映射 |
| `completion_validation.require_quality_gate: true` | `quality_gate_required: true` | 直接映射 |

---

## 七、Remediation 机制映射

### 7.1 remediation 循环映射

```yaml
# Spec-Global
remediation:
  enabled: true
  max_attempts: 5
  on_failure:
    action: "remediate"
    rollback_to: "responsible_step"
  step_mapping:
    - issue: "code_coverage"
      pattern: "代码覆盖率.*不达标"
      responsible_step: "p6_unit_test"

# v3.1 (状态机循环)
remediation:
  enabled: true
  max_attempts: 5
  retry_from_step: "p6_unit_test"
  failure_patterns:
    - pattern: "代码覆盖率.*不达标"
      target_step: "p6_unit_test"
      remediation_action: "补充单元测试，提高覆盖率至 80% 以上"
```

### 7.2 remediation 状态转换

```
┌─────────────────────────────────────────────────────────────┐
│              Spec-Global Remediation 流程                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  p11_phase_acceptance (验收)                                │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐                                    │
│  │ 验收检查             │                                    │
│  └─────────┬───────────┘                                    │
│            │                                                │
│    ┌───────┴────────┐                                       │
│    │                │                                       │
│  PASS            FAIL                                         │
│    │                │                                       │
│    ▼                ▼                                        │
│ [完成]         ┌─────────────────────┐                     │
│              │ attempt_count < 5?   │                     │
│              └─────┬─────────────────┘                     │
│                    │                                       │
│              ┌─────┴──────┐                                │
│              │           │                                │
│            YES          NO                                │
│              │           │                                │
│              ▼           ▼                                │
│      ┌───────────┐  ┌───────────┐                        │
│      │ Remediate │  │ Human Gate │                        │
│      │ (自动)     │  │ (人工)     │                        │
│      └─────┬─────┘  └─────┬─────┘                        │
│            │             │                               │
│            └───────┬─────┘                               │
│                    │                                       │
│                    ▼                                       │
│            ┌─────────────────────┐                          │
│            │ 回滚到 responsible_step│                          │
│            └─────────────────────┘                          │
│                    │                                       │
│                    └───────────────────────────────►    │
│              重新执行验收 (p11)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 remediation 字段映射

| Spec-Global 字段 | v3.1 处理方式 | 映射规则 |
|-----------------|--------------|---------|
| `enabled: true` | `remediation_enabled: true` | 直接映射 |
| `max_attempts: 5` | `max_retries: 5` | 重命名 |
| `on_failure.rollback_to` | `retry_from_step` | 重命名 |
| `step_mapping[].pattern` | `failure_pattern` | 正则表达式 |
| `step_mapping[].responsible_step` | `target_step` | 目标步骤 |
| `step_mapping[].remediation_action` | `remediation_action` | 修复动作描述 |

---

## 八、路径变量解析映射

### 8.1 变量引用映射

| Spec-Global 变量 | v3.1 解析 | 示例值 |
|----------------|----------|--------|
| `$inputs.prd` | 从 workflow input 引用 | `prd/sample.md` |
| `$outputs.development_plan.phases` | 从前面 step output 引用 | `["phase1", "phase2"]` |
| `$phase_contract.inputs.requirement_source` | 从 contract 引用 | `requirements/auth.md` |
| `{phase_dir}` | 从 workflow 实例数据引用 | `04-phases/phase-auth/` |
| `{project_dir}` | 从项目配置引用 | `project/running-coach/` |

### 8.2 路径解析规则

```python
# v3.1 路径解析器
class PathResolver:
    def resolve(self, template_path: str, context: Dict) -> str:
        """
        解析 Spec-Global 的模板路径

        Examples:
            "$inputs.prd" → context["inputs"]["prd"]
            "{phase_dir}/openspec/" → context["phase_dir"] + "/openspec/"
            "{project_dir}/knowledge/" → context["project_config"]["knowledge_path"]
        """
        # 变量替换
        if template_path.startswith("$"):
            var_path = template_path[1:]  # 去掉 $
            return self._resolve_variable(var_path, context)

        # 占位符替换
        if "{" in template_path and "}" in template_path:
            return self._resolve_placeholder(template_path, context)

        # 直接路径
        return template_path
```

---

## 九、执行流程映射对照

### 9.1 Spec-Global → v3.1 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│         Spec-Global Workflow 执行流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. WorkflowLoader 加载 workflow.yaml                        │
│       │                                                     │
│       ├─→ 解析 stages[]                                      │
│       ├─→ 提取 steps[] (扁平化)                               │
│       ├─→ 提取 human_in_the_loop[] → gates[]                  │
│       └─→ 注册到 TemplateManager                               │
│                                                             │
│  2. Orchestrator 创建 WorkflowInstance                         │
│       │                                                     │
│       ├─→ workflow_id = "wf_dept_dev_001"                     │
│       ├─→ level = department (从 _metadata.yaml)             │
│       ├─→ template_id = "workflow.dev.development_pipeline"   │
│       └─→ status = pending                                    │
│                                                             │
│  3. StateMachine 计算就绪步骤                                 │
│       │                                                     │
│       └─→ get_ready_steps(workflow_id)                       │
│           → [s3_0_1_project_setup]                           │
│                                                             │
│  4. Executor 执行步骤                                          │
│       │                                                     │
│       ├─→ AgentLoader 加载 agent.dev.tech_lead                │
│       ├─→ 构建执行上下文                                       │
│       ├─→ LLMExecutor 调用 LLM                                │
│       └─→ 返回 output                                         │
│                                                             │
│  5. ContractLoader 验证输出                                  │
│       │                                                     │
│       ├─→ validate_output(contract_id, output)               │
│       ├─→ 验证失败？                                          │
│       │   ├─ Yes → WorkflowStatus.BLOCKED                     │
│       │   └─→ No  → 继续                                       │
│                                                             │
│  6. 检查 Gate                                                │
│       │                                                     │
│       ├─→ 有 gate？                                           │
│       │   ├─→ Yes → 等待审批 (WorkflowStatus.PAUSED)         │
│       │   └─→ No  → 继续下一步                               │
│                                                             │
│  7. 审批 Gate                                                │
│       │                                                     │
│       ├─→ approve_gate(workflow_id, gate_id, decision)        │
│       ├─→ 更新状态                                            │
│       └─→ 恢复执行 (WorkflowStatus.RUNNING)                    │
│                                                             │
│  8. 继续下一步 ...                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 状态转换映射

| Spec-Generic 状态 | v3.1 WorkflowStatus | 触发条件 |
|-------------------|-------------------|---------|
| (初始) | `PENDING` | WorkflowInstance 创建 |
| 执行中 | `RUNNING` | 第一个 step 开始执行 |
| 遇到 gate | `PAUSED` | `_handle_human_gate` 被调用 |
| 验证失败 | `BLOCKED` | Contract 验证失败 (策略 A) |
| 人工修复 | `BLOCKED` | 等待人工修复 |
| 完成 | `COMPLETED` | 所有 steps 完成 |
| 失败 | `FAILED` | 致命错误或审批拒绝 |

---

## 十、完整示例：dev workflow → v3.1

### 10.1 Spec-Global 原始片段

```yaml
# departments/dev/workflows/development-pipeline/v1/workflow.yaml
stages:
  - id: s3_1_dev_planning
    steps:
      - id: s3_1_1_development_planning
        name: 研发计划制定
        run: agent.dev.development_planner
        execution:
          model: prompt_switch
          timeout: 60m
        dependencies:
          requires: []
        inputs:
          - freeze_package:
              prd: $inputs.prd
              architecture: $inputs.architecture
        outputs:
          - path: "03-planning/development-plan.yaml"
            contract: ../../contracts/development-plan-contract/v1/schema.json
        output_validation:
          validation_mode: strict
          on_failure:
            action: retry
            max_retries: 2
        human_gate: h1_plan_review
```

### 10.2 v3.1 转换结果

```python
# v3.1 WorkflowTemplate.steps
steps=[
    StepTemplate(
        id="s3_1_1_development_planning",
        name="研发计划制定",
        stage_id="s3_1_dev_planning",
        executor_type="llm",
        agent_id="agent.dev.development_planner",
        execution_model=ExecutionModel(
            type="prompt_switch",
            config={"context_preservation": True}
        ),
        dependencies=[],
        inputs={
            "freeze_package": {
                "prd": "$inputs.prd",
                "architecture": "$inputs.architecture"
            }
        },
        outputs=[
            OutputSpec(
                path="03-planning/development-plan.yaml",
                contract="contract.dev.development_plan_contract"
            )
        ],
        validation_mode="strict",
        on_failure=OnFailure(
            action="retry",
            max_retries=2
        ),
        gates=["gate.dev.h1_plan_review"]
    )
]
```

---

## 十一、映射验证清单

在实现 WorkflowLoader 时，使用以下清单验证映射正确性：

### 11.1 基础映射验证

- [ ] `id` 字段正确映射
- [ ] `name` 字段正确映射
- [ ] `version` 字段正确映射
- [ ] `level` 从 `_metadata.yaml` 正确读取
- [ ] `description` 字段正确映射

### 11.2 Steps 映射验证

- [ ] `stages[].steps[]` 正确扁平化为 `steps[]`
- [ ] `stage_id` 正确保留
- [ ] `run` 字段正确解析为 `agent_id` 或 `skill_id`
- [ ] `dependencies.requires` 正确映射
- [ ] `inputs` 字典正确映射
- [ ] `outputs` 数组正确映射
- [ ] `outputs[].contract` 正确提取

### 11.3 Gates 映射验证

- [ ] `human_gate` 字段正确提取
- [ ] gate_id 正确添加前缀 `gate.{dept}.`
- [ ] `gate.type` 正确映射
- [ ] `gate.blocking` 正确映射
- [ ] `timeout.duration` 正确转换为 ms
- [ ] `required_roles` 正确映射
- [ ] `checklist` 正确映射

### 11.4 Contract 映射验证

- [ ] `outputs[].contract` 路径正确解析
- [ ] contract_id 正确生成
- [ ] ContractLoader 能正确加载 schema
- [ ] SchemaValidator 能正确验证

### 11.5 Agent 映射验证

- [ ] `agent_resources` 正确扫描
- [ ] agent_id 正确提取
- [ ] execution_model 正确映射
- [ ] persona_file 路径正确解析

---

## 十二、常见问题排查

### Q1: 某个 step 的 dependencies 不生效？

**检查清单**:
1. `dependencies.requires` 是否正确解析？
2. 依赖的 step_id 是否存在？
3. 是否有循环依赖？

### Q2: Gate 没有被触发？

**检查清单**:
1. `human_gate` 字段是否正确提取？
2. gate 是否正确注册到 `WorkflowTemplate.gates[]`？
3. Step 执行完成后是否检查了 gates？

### Q3: Contract 验证失败但没有 BLOCKED？

**检查清单**:
1. `output_validation.validation_mode` 是否正确解析？
2. ContractLoader 是否正确加载 schema？
3. 验证失败时是否正确更新状态？

### Q4: Agent 调用失败？

**检查清单**:
1. agent_id 是否正确从 `run` 字段提取？
2. AgentLoader 是否能找到 agent.yaml？
3. LLMExecutor 是否正确构建执行上下文？

---

**文档版本**: 1.0
**最后更新**: 2026-01-28
**维护者**: LEE Architecture Team
**状态**: ✅ 初稿完成
