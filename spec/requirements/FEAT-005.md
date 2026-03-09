# FEAT-005 执行自动检查门禁

## Summary
把 step_outputs 扁平化并执行 blocker/major 表达式。

## Goal
把 step_outputs 扁平化并执行 blocker/major 表达式。

## User Value
用户可以获得 gate pass/fail result，并完成 执行自动检查门禁 对应业务目标。

## Parent EPIC
- `EPIC-002`

## Capability Linkage
- `CAP-002 工作流执行与门禁控制`

## Scope
- 构建 gate evaluation context。
- 在 gate fail 时阻塞或失败 workflow。

## Preconditions
- 上游已提供完成该能力所需输入：gate expression、step_outputs。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 执行自动检查门禁 后，系统读取并校验所需输入，进入 把 step_outputs 扁平化并执行 blocker/major 表达式。 对应处理流程。
- 处理过程中应用核心业务规则：freeze 模式要求 blocker 与 major 均为 0。
- 完成后输出并落库/回传：gate pass/fail result。

## Processing
- 触发 执行自动检查门禁 后，系统读取并校验所需输入，进入 把 step_outputs 扁平化并执行 blocker/major 表达式。 对应处理流程。
- 处理过程中应用核心业务规则：freeze 模式要求 blocker 与 major 均为 0。
- 完成后输出并落库/回传：gate pass/fail result。

## Inputs
- gate expression
- step_outputs

## Outputs
- gate pass/fail result

## Business Rules
- freeze 模式要求 blocker 与 major 均为 0。
- gate 上下文允许直接访问 review 输出中的标量字段。

## Dependencies
- 依赖上游提供：gate expression、step_outputs

## Non-goals
- 在 gate fail 时阻塞或失败 workflow。

## Edge Cases
- 当 gate expression 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 执行自动检查门禁 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：gate pass/fail result。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 review 输出 blocker_count=0 时 draft/publish gate 可通过。
- AC-002 freeze 模式下 major_count>0 会触发 gate fail。

## Acceptance Checks
### AC-001 review 输出 blocker_count=0 时 draft/publish gate 可通过。
- Given: 已满足前置条件，且提供 gate expression。
- When: 触发 执行自动检查门禁 主流程。
- Then: review 输出 blocker_count=0 时 draft/publish gate 可通过。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 freeze 模式下 major_count>0 会触发 gate fail。
- Given: 系统处于 执行自动检查门禁 处理中，且相关规则已生效。
- When: 执行与 freeze 模式下 major_count>0 会触发 gate fail。 对应的业务步骤。
- Then: 系统应输出/更新：gate pass/fail result
- Trace Hints: TASK, TESTSET, TECH

## Delivery Metadata
- Priority: `P1`
- Delivery Slice: `reverse-draft`
- Lifecycle Status: `draft`

## Derived Object Expectations
- task_required: `True`
- testset_required: `True`
- testset_owner: `qa`
- qa_seed_required: `True`

## Code Refs
- `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`

## Source Refs
- `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
