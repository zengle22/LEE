# FEAT-009 审批人工门禁

## Summary
通过 CLI 审批 gate 并推动 workflow 继续执行。

## Goal
通过 CLI 审批 gate 并推动 workflow 继续执行。

## User Value
用户可以获得 approved gate state，并完成 审批人工门禁 对应业务目标。

## Parent EPIC
- `EPIC-003`

## Capability Linkage
- `CAP-003 CLI 工作流操作`

## Scope
- 读取 gate id、approver 与审批动作。
- 调用 gate API 更新 gate 状态。

## Preconditions
- 上游已提供完成该能力所需输入：workflow_id、gate_id、approver。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 审批人工门禁 后，系统读取并校验所需输入，进入 通过 CLI 审批 gate 并推动 workflow 继续执行。 对应处理流程。
- 处理过程中应用核心业务规则：只有 human gate 允许人工审批。
- 完成后输出并落库/回传：approved gate state。

## Processing
- 触发 审批人工门禁 后，系统读取并校验所需输入，进入 通过 CLI 审批 gate 并推动 workflow 继续执行。 对应处理流程。
- 处理过程中应用核心业务规则：只有 human gate 允许人工审批。
- 完成后输出并落库/回传：approved gate state。

## Inputs
- workflow_id
- gate_id
- approver

## Outputs
- approved gate state

## Business Rules
- 只有 human gate 允许人工审批。
- 审批后 workflow 需可继续推进。

## Dependencies
- 依赖上游提供：workflow_id、gate_id

## Non-goals
- 调用 gate API 更新 gate 状态。

## Edge Cases
- 当 workflow_id 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 审批人工门禁 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：approved gate state。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 approve 命令能更新 gate 记录。
- AC-002 审批成功后 workflow 不再停留在原 gate。

## Acceptance Checks
### AC-001 approve 命令能更新 gate 记录。
- Given: 已满足前置条件，且提供 workflow_id。
- When: 触发 审批人工门禁 主流程。
- Then: approve 命令能更新 gate 记录。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 审批成功后 workflow 不再停留在原 gate。
- Given: 系统处于 审批人工门禁 处理中，且相关规则已生效。
- When: 执行与 审批成功后 workflow 不再停留在原 gate。 对应的业务步骤。
- Then: 系统应输出/更新：approved gate state
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
- `src/lee/cli/commands/approve.py`
- `src/lee/orchestrator/execution/gate_api.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/cli/commands/approve.py`
- `src/lee/orchestrator/execution/gate_api.py`

## Source Refs
- `src/lee/cli/commands/approve.py`
- `src/lee/orchestrator/execution/gate_api.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
