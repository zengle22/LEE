# FEAT-004 执行工作流步骤 DAG

## Summary
根据 depends_on 选择 ready step 并顺序推进 workflow。

## Goal
根据 depends_on 选择 ready step 并顺序推进 workflow。

## User Value
用户可以获得 completed_steps，并完成 执行工作流步骤 DAG 对应业务目标。

## Parent EPIC
- `EPIC-002`

## Capability Linkage
- `CAP-002 工作流执行与门禁控制`

## Scope
- 处理 step 调度、继续执行与完成汇总。
- 支持 skill、agent、gate 等步骤类型。

## Preconditions
- 上游已提供完成该能力所需输入：workflow instance、current step state。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 执行工作流步骤 DAG 后，系统读取并校验所需输入，进入 根据 depends_on 选择 ready step 并顺序推进 workflow。 对应处理流程。
- 处理过程中应用核心业务规则：只有所有依赖满足后步骤才可执行。
- 完成后输出并落库/回传：completed_steps、next ready step、workflow summary。

## Processing
- 触发 执行工作流步骤 DAG 后，系统读取并校验所需输入，进入 根据 depends_on 选择 ready step 并顺序推进 workflow。 对应处理流程。
- 处理过程中应用核心业务规则：只有所有依赖满足后步骤才可执行。
- 完成后输出并落库/回传：completed_steps、next ready step、workflow summary。

## Inputs
- workflow instance
- current step state

## Outputs
- completed_steps
- next ready step
- workflow summary

## Business Rules
- 只有所有依赖满足后步骤才可执行。
- 失败步骤必须显式标记 workflow 状态。

## Dependencies
- 依赖上游提供：workflow instance、current step state

## Non-goals
- 支持 skill、agent、gate 等步骤类型。

## Edge Cases
- 当 workflow instance 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 执行工作流步骤 DAG 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：completed_steps、next ready step、workflow summary。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 多步 workflow 可按 depends_on 连续推进。
- AC-002 失败时 workflow 状态变为 failed。

## Acceptance Checks
### AC-001 多步 workflow 可按 depends_on 连续推进。
- Given: 已满足前置条件，且提供 workflow instance。
- When: 触发 执行工作流步骤 DAG 主流程。
- Then: 多步 workflow 可按 depends_on 连续推进。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 失败时 workflow 状态变为 failed。
- Given: 系统处于 执行工作流步骤 DAG 处理中，且相关规则已生效。
- When: 执行与 失败时 workflow 状态变为 failed。 对应的业务步骤。
- Then: 系统应输出/更新：next ready step
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
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/state_machine.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/state_machine.py`

## Source Refs
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/state_machine.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
