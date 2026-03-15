---
id: TECH-FEAT-SRC-041-001
ssot_type: tech
title: ADR-017 Gate 双轴语义与人工审批收敛 Frozen 技术架构
status: frozen
version: v1
workflow_instance_id: adr-017-gate-governance-impl
parent_id: FEAT-SRC-041-001
derived_from_ids:
  - FEAT-SRC-041-001
  - FEAT-SRC-041-002
  - FEAT-SRC-041-003
  - FEAT-SRC-041-004
  - FEAT-SRC-041-005
  - ADR-017
source_refs:
  - FEAT-SRC-041-001
  - FEAT-SRC-041-002
  - FEAT-SRC-041-003
  - FEAT-SRC-041-004
  - FEAT-SRC-041-005
  - ADR-017#Decision
  - ADR-017#Allowed Combinations
  - ADR-017#Human Gate Context Contract
  - ADR-017#Gate Flow And Workflow State Machine
owner: architect
tags:
  - gate
  - approval
  - cli
  - runtime
  - audit
  - governance
properties:
  contract_key: tech_spec
  identity_kind: ssot
frozen_at: "2026-03-15T05:28:24Z"
---

contract_type: frozen-technical-architecture
contract_version: "1.0"
metadata:
  contract_id: FTA-20260315-041
  title: ADR-017 Gate 双轴语义与人工审批收敛 Frozen 技术架构
  description: 面向 EPIC-SRC-041-016 的 gate 语义收敛、人工审批上下文、CLI 摘要与统一 gate_result 输出技术方案
  status: FROZEN
  is_frozen: true
  frozen_at: "2026-03-15T05:28:24Z"
  epic_ref: EPIC-SRC-041-016
  feat_bundle:
    - FEAT-SRC-041-001
    - FEAT-SRC-041-002
    - FEAT-SRC-041-003
    - FEAT-SRC-041-004
    - FEAT-SRC-041-005
  governing_adr: ADR-017
  designer: Architecture Designer
  reviewer: 待人类核准
  reviewer_approval_pending: true

# 1. 架构目标与边界

## 1.1 目标

本架构冻结以下技术目标：

- 以 `purpose` 与 `decision_mode` 作为 gate 的唯一正式治理语义，替代旧的 `gate_type / human_gate / human_review / human_approval` 混合分类。
- 把 `human_gate_context` 固定为所有 `decision_mode=human_required` 以及自动升级到人工决策场景的统一前置对象。
- 把 CLI `list / show / decide` 三条链路统一到同一套可判断摘要模型上，阻断 view-model 平行命名。
- 把人工决策结果统一收口为 `gate_result`，使 runtime、CLI、trace、审计消费同一个稳定对象。
- 对 freeze、release、merge、risk acceptance 这类正式边界动作实施 `approval + human_required` 的强约束，并在运行时 fail-closed。

## 1.2 非目标

- 不在本技术架构中冻结数据库最终列名或一次性历史回填脚本。
- 不在本技术架构中设计前端 UI 交互细节。
- 不引入新的平行审批系统、平行 gate registry 或独立人审服务。

## 1.3 仓库现状锚点

本方案基于以下既有模块收敛，不新建旁路：

- `src/lee/orchestrator/execution/gate_operations.py`
- `src/lee/orchestrator/execution/gate_api.py`
- `src/lee/orchestrator/execution/human_approval.py`
- `src/lee/cli/commands/gates_cmd.py`
- `src/lee/orchestrator/storage/models.py`
- `src/lee/orchestrator/execution/trace.py`
- `src/lee/orchestrator/execution/runners/normalization/review_semantics.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`
- `spec/adr/ADR-017__gate-zhizeyujuecemoshifencengyurenjishenpipinshenjiaohu.md`

# 2. 技术选型

## 2.1 核心技术栈

| 层级 | 技术选型 | 版本约束 | 选型理由 |
|------|----------|----------|----------|
| 运行时 | Python | `>=3.8` | 仓库 `pyproject.toml` 已冻结 Python 运行时，无需引入新语言栈 |
| CLI 框架 | Click | `>=8.1` | 现有 `lee` 命令体系基于 Click，适合继续扩展 gates 子命令 |
| 序列化 | PyYAML + JSON | `pyyaml>=6.0` | 规格文档、workflow、gate payload 已大量使用 YAML/JSON |
| Schema 校验 | jsonschema | `>=4.0` | 已存在 schema validator，可承接 gate 对象契约校验 |
| 存储 | SQLite + aiosqlite | `aiosqlite>=0.19` | 当前 workflow / gate 状态权威在 SQLite，继续沿用最稳妥 |
| 审计与追踪 | JSONL trace + artifact refs | 内置 | `trace.py` 已提供 gate span 与 artifact 引用能力 |
| 模板与 workflow | 现有 workflow template + template manager | 当前仓库实现 | 不新增新模板引擎，保持 spec-global 与 runtime 一致 |

## 2.2 关键依赖项

### 内部依赖

- `lee.orchestrator.execution.gate_operations.GateOperationsMixin`
- `lee.orchestrator.execution.gate_api.GateAPI`
- `lee.orchestrator.execution.human_approval.HumanApprovalExecutor`
- `lee.cli.commands.gates_cmd`
- `lee.orchestrator.storage.models`
- `lee.orchestrator.execution.trace.TraceLog`
- `lee.orchestrator.execution.state_machine`
- `lee.orchestrator.execution.artifacts.ssot_contract.SSOTContractMaterializer`

### 外部依赖

- `click>=8.1`
- `pyyaml>=6.0`
- `jsonschema>=4.0`
- `aiosqlite>=0.19`
- `aiohttp>=3.9`，仅保留为后续审批 API 外露的预留能力，不作为当前主路径

# 3. 冻结的核心设计决策

## 3.1 Gate 语义单一真相源

所有 gate 定义的正式真相源固定为：

- `purpose`: `review | approval`
- `decision_mode`: `auto | conditional_human | human_required`

运行时不得再把以下字段视为正式分类轴：

- `gate_type`
- `human_gate`
- `human_review`
- `human_approval`
- `Auto Gate / Review Gate / Approval Gate`

这些值只允许出现在兼容映射入口与历史识别逻辑中。

## 3.2 合法组合与禁止组合

第一阶段仅允许以下组合：

- `review + auto`
- `review + conditional_human`
- `review + human_required`
- `approval + human_required`

第一阶段显式禁止：

- `approval + auto`
- `approval + conditional_human`

当 `boundary_action in {freeze, release, merge, risk_acceptance}` 时，运行时必须同时满足：

- `purpose == approval`
- `decision_mode == human_required`
- `human_gate_context` 完整

任一条件不成立时，gate 视为不合规定义，不允许进入待审批状态。

## 3.3 旧分类兼容映射

| legacy 输入 | 收敛结果 | 说明 |
|-------------|----------|------|
| `auto_check` | `review + auto` | 仅表示机器审查 |
| `human_review` | `review + human_required` | 表示人工评审，不构成正式放行 |
| `human_approval` | `approval + human_required` | 表示正式人工审批 |
| `human_gate` | 运行时必须根据上下文映射；缺乏足够信息时拒绝 materialize 为正式语义 | 禁止继续原样下发 |
| `Auto Gate` | `review + auto` | 历史治理称呼，仅作兼容入口 |
| `Review Gate` | `review + human_required` 或 `review + conditional_human` | 需由输入显式补足是否升级 |
| `Approval Gate` | `approval + human_required` | 正式放行边界 |

`human_gate` 与 `Review Gate` 若不能从原始配置、安全规则或 boundary_action 明确推出正式语义，系统必须 fail-closed，而不是猜测。

# 4. 模块级实现方案

## 4.1 语义收敛层

### 目标

把 FEAT/ADR 的治理语义编译成 runtime 可消费的唯一 gate read model。

### 实现方案

- 在 `src/lee/orchestrator/execution` 下新增单一语义模块，例如 `gate_semantics.py`，定义：
  - `GatePurpose`
  - `GateDecisionMode`
  - `BoundaryAction`
  - `LEGACY_GATE_MAPPING`
  - `validate_gate_semantics()`
- 现有 `runners/normalization/review_semantics.py` 与 `workflow_generator.py` 只负责把 spec/workflow 输入归一化为上述 read model，不再各自维护映射表。
- `gate_operations.py`、`gate_api.py`、`gates_cmd.py`、`trace.py` 一律通过该模块读取 `purpose / decision_mode / boundary_action`，避免重复判断。

### 冻结输出对象

```yaml
gate_definition:
  gate_definition_id: string
  purpose: review | approval
  decision_mode: auto | conditional_human | human_required
  boundary_action: freeze | release | merge | risk_acceptance | null
  legacy_gate_type: string | null
  legacy_mapping_applied: boolean
  compliance_status: valid | invalid
  invalid_reason: string | null
```

### 关键约束

- `purpose` 或 `decision_mode` 任一缺失即 `compliance_status=invalid`
- `approval` 不允许被 runtime 自动改写为 `review`
- `boundary_action` 为正式边界动作时不允许空值

## 4.2 Human Gate Context 装配层

### 目标

在 gate 进入待审批前组装统一的 `human_gate_context`，供 runtime、CLI、trace、审计复用。

### 实现方案

- 新增 `gate_context_builder.py`，由 `gate_operations.py` 在创建 gate 或升级 gate 时调用。
- 输入来源固定为：
  - `gate_definition`
  - `workflow instance`
  - `step_outputs`
  - `candidate package / review report / test evidence`
  - 自动升级场景的 `escalation_reason`
- `gate_context_builder` 输出结构化对象，同时回填 `pending_gate_summary` 所需的 `subject / why_now / purpose / decision_mode` 摘要字段。
- `GateAPI.create_gate()` 与 `HumanApprovalExecutor.create_request()` 只接受 builder 产出的上下文对象，不再直接接收松散 `context_data`。

### 冻结输出对象

```yaml
human_gate_context:
  gate_id: string
  gate_definition_id: string
  purpose: review | approval
  decision_mode: human_required
  workflow_id: string
  step_id: string
  boundary_action: string | null
  subject:
    title: string
    type: step | artifact | freeze_bundle | release_bundle | merge_bundle | risk_bundle
  subject_refs:
    - string
  why_now: string
  escalation_reason: string | null
  evidence_refs:
    - string
  risk_summary: string
  next_action:
    recommended: continue | retry | rollback | spawn | terminate | continue_with_risk | hold
    alternatives:
      - string
  repo_context:
    workspace_root: string
    affected_paths:
      - string
    related_but_untouched:
      - string
```

### 关键约束

- `subject`、`subject_refs`、`why_now`、`evidence_refs`、`risk_summary`、`next_action.recommended` 必填
- 自动升级场景 `escalation_reason` 必填
- `repo_context` 只允许表达审批所需的仓库路径上下文，不承担完整代码分析职责

## 4.3 审批执行与状态机层

### 目标

在现有 `approve / reject / revise / flag` 基础上引入基于 `purpose / decision_mode / next_action` 的一致决策语义。

### 实现方案

- 扩展 `gate_operations.py`，在 gate 决策前执行：
  - `gate_definition` 合规校验
  - `boundary_action` 合规校验
  - `human_gate_context` 完整性校验
  - `decision` 与 `next_action` 组合校验
- `review` 允许：
  - `approve`
  - `revise`
  - `reject`
  - `flag`
- `approval` 只允许：
  - `approve`
  - `reject`
- `flag` 只属于 `review`
- `reject` 必须显式绑定 `next_action in {rollback, spawn, terminate}`
- `revise` 必须显式绑定 `next_action=retry`
- 继续沿用现有 `rewind_to`、`spawn workflow`、`workflow paused/running/superseded` 机制，不新写旁路状态机

### 冻结输出对象

```yaml
gate_result:
  gate_id: string
  gate_definition_id: string
  purpose: review | approval
  decision_mode: auto | conditional_human | human_required
  decision: approve | reject | revise | flag
  decision_by: string
  decision_at: string
  subject_refs:
    - string
  evidence_refs:
    - string
  risk_summary: string
  next_action: continue | retry | rollback | spawn | terminate | continue_with_risk | hold
  comments: string
  structured_feedback: object | null
  context_ref: string
```

### 关键约束

- `subject_refs`、`evidence_refs`、`next_action` 在所有人工 gate 结果中必填
- `approval` 结果不允许 `decision=flag`
- `approval + approve` 之后才允许 materialize `*_freeze_ref`、`merge_decision_ref`、`release_decision_ref`

## 4.4 CLI 投影视图层

### 目标

让 `lee gates list/show/decide` 消费同一上下文与结果对象，不再各自定义摘要字段。

### 实现方案

- `gates_cmd.py` 改为从统一的 gate projection adapter 读取：
  - `pending_gate_summary`
  - `human_gate_context`
  - `gate_result`
- `list` 只展示最小可判断摘要：
  - `purpose`
  - `decision_mode`
  - `subject`
  - `why_now`
- `show` 以区块化方式渲染 `human_gate_context`
- `decide` 先展示摘要，再选择决策，再展示决策后果预览，最后提交
- 现有直接读数据库并拼字段的方式保留为兼容读取层，但不再是最终展示模型

### 冻结输出对象

```yaml
pending_gate_summary:
  gate_id: string
  workflow_id: string
  step_id: string
  purpose: review | approval
  decision_mode: auto | conditional_human | human_required
  subject: string
  why_now: string
  status: pending | approved | rejected | revised | flagged | invalidated
  created_at: string
```

### 关键约束

- `list` 不允许只展示 `gate_id / step_id / status`
- `show` 与 `decide` 必须复用同名字段，不允许二次命名
- CLI 读不到 `pending_gate_summary` 时，应提示 gate 数据不合规，而不是静默降级为旧字段

## 4.5 持久化与审计层

### 目标

使 gate 语义、上下文引用和统一结果可追溯，并与现有 workflow/gate 表结构兼容演进。

### 实现方案

- `storage/models.py` 中的 `GateApproval` 保持为权威状态对象，但扩展以下信息的存储或引用：
  - `purpose`
  - `decision_mode`
  - `boundary_action`
  - `context_ref`
  - `result_ref`
- 通过新的 SQLite migration 为 `.workflow/orchestrator.db` 增补字段；若短期不宜强制迁移，则先把扩展信息落入 JSON 列并保留迁移路径。
- `trace.py` 的 gate span 从 `gate_type` 迁移为：
  - `purpose`
  - `decision_mode`
  - `decision`
  - `evidence_refs`
- 所有人工决策在 trace 中记录 `context_ref` 与 `gate_result` hash，用于审计回放。

### 关键约束

- SQLite 仍是 gate 状态权威
- trace 是事实回放层，不承担语义推断
- `context_ref` 与 `result_ref` 必须能定位到 artifact 或结构化 blob，而不是 CLI 临时字符串

## 4.6 兼容迁移层

### 目标

在不一次性重写全部 gate 模板的前提下，把旧分类逐步收敛到新模型。

### 实现方案

- workflow/gate 模板读取时优先消费 `purpose / decision_mode`
- 若只存在旧字段，则先套用兼容映射，再执行合规校验
- 对 `human_gate` 这类信息不足的旧值：
  - 非正式边界动作可临时映射为 `review + human_required`
  - 正式边界动作一律要求人工补齐正式字段，否则阻断
- 在 `runners/llm_runner.py` 与规格 normalizer 中加入 lint，禁止新下发产物继续产出单轴旧分类

### 关键约束

- 兼容层只能作为输入侧 adapter，不能成为输出侧正式 schema
- 新增 gate 定义必须直接写双轴字段

# 5. 对 FEAT 的实现映射

| FEAT | 技术响应 | 主要落点 |
|------|----------|----------|
| `FEAT-SRC-041-001` | 冻结 `purpose / decision_mode` 枚举、允许组合、legacy 映射、fail-closed 规则 | `gate_semantics.py`、normalization 层、workflow/gate lint |
| `FEAT-SRC-041-002` | 冻结 `human_gate_context` 最小字段、校验时机、升级场景补齐规则 | `gate_context_builder.py`、`gate_api.py`、`human_approval.py` |
| `FEAT-SRC-041-003` | 对正式边界动作执行 `approval + human_required` 强约束 | `gate_operations.py`、workflow gate 校验、approval policy |
| `FEAT-SRC-041-004` | 统一 `pending_gate_summary` 与 `list/show/decide` 读模型 | `gates_cmd.py`、CLI projection adapter |
| `FEAT-SRC-041-005` | 统一人工决策结果为 `gate_result` 并绑定 trace/audit | `gate_operations.py`、`trace.py`、artifact refs |

# 6. 核心依赖与文件触点

## 6.1 代码触点

- `src/lee/orchestrator/execution/gate_operations.py`
- `src/lee/orchestrator/execution/gate_api.py`
- `src/lee/orchestrator/execution/human_approval.py`
- `src/lee/cli/commands/gates_cmd.py`
- `src/lee/orchestrator/storage/models.py`
- `src/lee/orchestrator/storage/migrations/`
- `src/lee/orchestrator/execution/trace.py`
- `src/lee/orchestrator/execution/runners/normalization/review_semantics.py`
- `src/lee/orchestrator/execution/runners/llm_runner.py`

## 6.2 规格与治理触点

- `spec/adr/ADR-017__gate-zhizeyujuecemoshifencengyurenjishenpipinshenjiaohu.md`
- `spec/requirements/SRC-041/FEAT-SRC-041-001__gate-purpose-yu-decision-mode-mubiaoyuyidongjie.md`
- `spec/requirements/SRC-041/FEAT-SRC-041-002__human-gate-context-rengongjueceqianzhishangxiawenq.md`
- `spec/requirements/SRC-041/FEAT-SRC-041-003__zhengshibianjiedongzuode-approval-plus-human-requi.md`
- `spec/requirements/SRC-041/FEAT-SRC-041-004__daishenpi-gate-dezuixiaokepanduanzhaiyaotongyi.md`
- `spec/requirements/SRC-041/FEAT-SRC-041-005__rengong-gate-juecejieguodetongyi-gate-result-shuch.md`

# 7. 高风险点与备份方案

## 7.1 风险一：旧 gate 分类存量过多，迁移期间出现双重语义

**风险描述**  
仓库现有实现和模板仍大量使用 `human_gate / human_review / human_approval / gate_type`，若同时保留旧输出与新输出，下游会继续各自解释。

**缓解措施**

1. 输入侧允许兼容映射，输出侧一律只发布双轴字段。
2. 为 `human_gate` 设置信息不足即阻断的 fail-closed 规则。
3. 在 normalizer 与测试中加入 lint，阻止新规范继续输出旧分类。

**备份方案**

- 若一次性迁移模板成本过高，先在 runtime adapter 层完成兼容映射，但保留一个全局开关统计 legacy 命中率。
- 对正式边界动作先强制完成改造，普通 review gate 允许短期兼容。

## 7.2 风险二：`human_gate_context` 与 CLI 摘要不一致

**风险描述**  
若 `list/show/decide` 继续分别查库拼字段，将出现 `subject`、`why_now`、`purpose` 命名不一致。

**缓解措施**

1. 统一由 `gate_context_builder` 回填 `pending_gate_summary`。
2. `gates_cmd.py` 仅消费 projection adapter，不再直接定义摘要字段。
3. 把 `repo_context` 的来源限制为 workspace path 与 affected paths，防止视图层擅自扩展。

**备份方案**

- 若 CLI 重构切面过大，第一阶段先替换 `show/decide`，并让 `list` 读取同一 summary blob。
- 最差情况下保留旧命令壳，但强制它们打印统一 summary。

## 7.3 风险三：正式边界动作仍可能绕过 `approval + human_required`

**风险描述**  
当前 `approve_gate` 逻辑已能直接恢复 workflow；若缺乏边界动作校验，freeze、merge 仍可能被 review 语义放行。

**缓解措施**

1. 在 `gate_operations.py` 决策前增加边界动作合规校验。
2. `approval + approve` 之外禁止生成正式 `*_freeze_ref` 或正式决议对象。
3. 把该校验放入状态机入口，而不是只放在 CLI。

**备份方案**

- 若短期内无法在所有入口统一校验，先在 `gate_operations.py` 和 `workflow_runner.py` 两处兜底阻断。
- 对旧 workflow 直接打 warning 不够，正式边界一律 blocking。

## 7.4 风险四：SQLite 迁移影响现有 gate 记录读取

**风险描述**  
`GateApproval` 新增语义字段与引用字段后，历史数据库实例可能无法立即升级。

**缓解措施**

1. 采用向后兼容 migration，新增列默认允许空值。
2. 在读路径上允许从 JSON 扩展字段恢复 `purpose / decision_mode / context_ref / result_ref`。
3. 保留旧记录读取能力，不要求一次性回填历史 gate。

**备份方案**

- 若 schema 迁移窗口受限，先把语义扩展写入 `structured_feedback` 或等价 JSON 扩展位，再安排后续迁移。
- 但新创建 gate 必须具备完整新字段，不允许继续创建旧格式。

## 7.5 风险五：`gate_result` 与 trace/audit 没有稳定绑定

**风险描述**  
若 `gate_result` 只出现在 CLI 返回值中，不进入 artifact/trace，后续无法审计“谁基于什么证据做了什么决策”。

**缓解措施**

1. `gate_result` 必须 materialize 为结构化输出或 blob，并生成 `result_ref`。
2. trace gate span 固定记录 `purpose / decision_mode / decision / evidence_refs / result_ref`。
3. `context_ref` 与 `result_ref` 必须可回放到审批对象与证据。

**备份方案**

- 若短期无法对 trace schema 做大改，先把 `result_ref` 和核心字段放入 span `attributes`，随后再升级正式 trace contract。

# 8. 技术不确定性与人类决策点

## 8.1 不确定性：`repo_context` 的最小边界

当前 FEAT 只要求 `repo_context` 存在，但未冻结到代码级来源。技术架构在第一阶段将其限定为：

- `workspace_root`
- `affected_paths`
- `related_but_untouched`

**备份方案**  
若后续发现审批需要更多上下文，扩展方式只能增加字段，不能改变前三项的含义。

## 8.2 不确定性：`conditional_human` 的升级判定粒度

ADR-017 已定义其存在，但仓库现有 runtime 仍偏向 `auto` 或直接 `human_required`。

**备份方案**  
第一阶段可先在 read model 中保留 `conditional_human`，但运行时只在自动检查升级链路启用；若实现复杂度过高，可先把存量都落为 `review + human_required`，同时保留升级原因字段。

## 8.3 不确定性：历史 gate 记录是否需要回填成新模型

本架构不要求一次性回填历史数据。

**备份方案**  
只保证新 gate 创建时符合新对象边界；历史记录通过兼容读取适配，不承担新审计能力承诺。

# 9. 验收映射与验证规则

| 验收项 | 技术验证点 | 阻断级别 |
|--------|------------|----------|
| `FEAT-001` 新增 gate 显式声明双轴字段 | `gate_definition.compliance_status == valid` | blocker |
| `FEAT-001` 旧分类只作兼容输入 | 新输出中不存在正式 `legacy_gate_type` 作为分类轴 | blocker |
| `FEAT-002` 人工审批前必须有 `human_gate_context` | gate 进入 pending 前通过 context completeness 校验 | blocker |
| `FEAT-002` 自动升级场景必须补齐升级原因 | `escalation_reason` 非空 | blocker |
| `FEAT-003` 正式边界动作固定为 `approval + human_required` | `boundary_action` 合规校验 | blocker |
| `FEAT-004` list/show/decide 共享同一摘要语义 | CLI projection snapshot 一致 | major |
| `FEAT-005` 人工 gate 统一输出 `gate_result` | `result_ref` 可追溯，且含 `subject_refs/evidence_refs/next_action` | blocker |

验证规则冻结如下：

- 缺少 `purpose` 或 `decision_mode` 的 gate 定义不得进入 pending。
- 缺少 `human_gate_context` 的人工 gate 不得进入 CLI 审批链路。
- `approval` gate 不得产生 `flag` 结果。
- `review approve` 不得 materialize 正式 `*_freeze_ref`。
- `gate_result.next_action` 与 `decision` 组合非法时必须阻断提交。

# 10. 人类核准栏位

```yaml
human_approval:
  approval_required: true
  approval_status: pending_human_review
  approver_role: Architecture Owner
  approval_checklist:
    - 双轴语义与 legacy 兼容映射是否清晰且无第三分类轴
    - human_gate_context 是否足以支撑人工首轮判断
    - 正式边界动作是否被强约束到 approval + human_required
    - gate_result 是否满足 runtime/CLI/audit 共用边界
    - 风险与备份方案是否覆盖迁移、CLI、一致性、审计
  signature_field: 待人类核准后填写
  approval_date_field: 待人类核准后填写
```

# 11. SSOT 输出合约

```yaml
contract_version: "1.0"
run_id: tech-feat-src-041-016
outputs:
  - key: tech_specs
    identity_kind: ssot
    ssot_type: tech
    title: ADR-017 Gate 双轴语义与人工审批收敛 Frozen 技术架构
    parent: EPIC-SRC-041-016
    derived_from:
      - FEAT-SRC-041-001
      - FEAT-SRC-041-002
      - FEAT-SRC-041-003
      - FEAT-SRC-041-004
      - FEAT-SRC-041-005
      - ADR-017
    source_refs:
      - FEAT-SRC-041-001
      - FEAT-SRC-041-002
      - FEAT-SRC-041-003
      - FEAT-SRC-041-004
      - FEAT-SRC-041-005
      - ADR-017#Decision
```

---

**状态**: FROZEN  
**冻结时间**: 2026-03-15T05:28:24Z  
**人类核准**: 待完成
