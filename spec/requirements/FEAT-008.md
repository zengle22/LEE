# FEAT-008 查询 workflow 状态

## Summary
查看 workflow 当前状态、完成步骤与 gate 信息。

## Goal
查看 workflow 当前状态、完成步骤与 gate 信息。

## User Value
用户可以获得 status summary，并完成 查询 workflow 状态 对应业务目标。

## Parent EPIC
- `EPIC-003`

## Capability Linkage
- `CAP-003 CLI 工作流操作`

## Scope
- 读取 workflow instance 数据。
- 向终端输出状态摘要。

## Preconditions
- 上游已提供完成该能力所需输入：workflow_id。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 查询 workflow 状态 后，系统读取并校验所需输入，进入 查看 workflow 当前状态、完成步骤与 gate 信息。 对应处理流程。
- 处理过程中应用核心业务规则：状态查询不修改 workflow 数据。
- 完成后输出并落库/回传：status summary。

## Processing
- 触发 查询 workflow 状态 后，系统读取并校验所需输入，进入 查看 workflow 当前状态、完成步骤与 gate 信息。 对应处理流程。
- 处理过程中应用核心业务规则：状态查询不修改 workflow 数据。
- 完成后输出并落库/回传：status summary。

## Inputs
- workflow_id

## Outputs
- status summary

## Business Rules
- 状态查询不修改 workflow 数据。
- 需要兼容 blocked、paused、failed、completed 等状态。

## Dependencies
- 依赖上游提供：workflow_id

## Non-goals
- 向终端输出状态摘要。

## Edge Cases
- 当 workflow_id 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 查询 workflow 状态 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：status summary。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 给定 workflow_id 可以输出当前状态与当前步骤。
- AC-002 blocked workflow 会显示 gate 指引。

## Acceptance Checks
### AC-001 给定 workflow_id 可以输出当前状态与当前步骤。
- Given: 已满足前置条件，且提供 workflow_id。
- When: 触发 查询 workflow 状态 主流程。
- Then: 给定 workflow_id 可以输出当前状态与当前步骤。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 blocked workflow 会显示 gate 指引。
- Given: 系统处于 查询 workflow 状态 处理中，且相关规则已生效。
- When: 执行与 blocked workflow 会显示 gate 指引。 对应的业务步骤。
- Then: 系统应输出/更新：status summary
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
- `src/lee/cli/commands/status.py`
- `src/lee/cli/main.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/cli/commands/status.py`
- `src/lee/cli/main.py`

## Source Refs
- `src/lee/cli/commands/status.py`
- `src/lee/cli/main.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
