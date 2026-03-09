# FEAT-006 持久化步骤输出与证据路径

## Summary
完成步骤时把 output dict 与 output paths 写入 workflow data。

## Goal
完成步骤时把 output dict 与 output paths 写入 workflow data。

## User Value
用户可以获得 workflow.data.step_outputs，并完成 持久化步骤输出与证据路径 对应业务目标。

## Parent EPIC
- `EPIC-002`

## Capability Linkage
- `CAP-002 工作流执行与门禁控制`

## Scope
- 保存 paths、stdout 元数据与结构化字段。
- 为后续 gate 和 $outputs 引用提供输入。

## Preconditions
- 上游已提供完成该能力所需输入：step output、output specs。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 持久化步骤输出与证据路径 后，系统读取并校验所需输入，进入 完成步骤时把 output dict 与 output paths 写入 workflow data。 对应处理流程。
- 处理过程中应用核心业务规则：同一步骤重复执行时路径列表需要去重合并。
- 完成后输出并落库/回传：workflow.data.step_outputs。

## Processing
- 触发 持久化步骤输出与证据路径 后，系统读取并校验所需输入，进入 完成步骤时把 output dict 与 output paths 写入 workflow data。 对应处理流程。
- 处理过程中应用核心业务规则：同一步骤重复执行时路径列表需要去重合并。
- 完成后输出并落库/回传：workflow.data.step_outputs。

## Inputs
- step output
- output specs

## Outputs
- workflow.data.step_outputs

## Business Rules
- 同一步骤重复执行时路径列表需要去重合并。
- 结构化 stdout 应合并到 step_outputs 顶层。

## Dependencies
- 依赖上游提供：step output、output specs

## Non-goals
- 为后续 gate 和 $outputs 引用提供输入。

## Edge Cases
- 当 step output 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 持久化步骤输出与证据路径 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：workflow.data.step_outputs。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 完成步骤后 step_outputs 中可读取 paths。
- AC-002 gate 表达式可以直接使用 review 产生的 blocker_count。

## Acceptance Checks
### AC-001 完成步骤后 step_outputs 中可读取 paths。
- Given: 已满足前置条件，且提供 step output。
- When: 触发 持久化步骤输出与证据路径 主流程。
- Then: 完成步骤后 step_outputs 中可读取 paths。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 gate 表达式可以直接使用 review 产生的 blocker_count。
- Given: 系统处于 持久化步骤输出与证据路径 处理中，且相关规则已生效。
- When: 执行与 gate 表达式可以直接使用 review 产生的 blocker_count。 对应的业务步骤。
- Then: 系统应输出/更新：workflow.data.step_outputs
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
- `src/lee/orchestrator/execution/state_machine.py`
- `src/lee/orchestrator/execution/runners/shell_runner.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/orchestrator/execution/state_machine.py`
- `src/lee/orchestrator/execution/runners/shell_runner.py`

## Source Refs
- `src/lee/orchestrator/execution/state_machine.py`
- `src/lee/orchestrator/execution/runners/shell_runner.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
