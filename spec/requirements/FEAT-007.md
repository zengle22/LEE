# FEAT-007 通过 CLI 运行 workflow

## Summary
支持 `lee run` 加载 registry、渲染模板并执行 workflow。

## Goal
支持 `lee run` 加载 registry、渲染模板并执行 workflow。

## User Value
用户可以获得 workflow instance，并完成 通过 CLI 运行 workflow 对应业务目标。

## Parent EPIC
- `EPIC-003`

## Capability Linkage
- `CAP-003 CLI 工作流操作`

## Scope
- 解析 workflow key 与 spec 文件。
- 触发 create、run_until_blocked 与 summary 输出。

## Preconditions
- 上游已提供完成该能力所需输入：workflow key、--spec、--project-dir。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 通过 CLI 运行 workflow 后，系统读取并校验所需输入，进入 支持 `lee run` 加载 registry、渲染模板并执行 workflow。 对应处理流程。
- 处理过程中应用核心业务规则：load_spec_as_params 的 workflow 必须把 spec 内容注入 params。
- 完成后输出并落库/回传：workflow instance、rendered template、execution summary。

## Processing
- 触发 通过 CLI 运行 workflow 后，系统读取并校验所需输入，进入 支持 `lee run` 加载 registry、渲染模板并执行 workflow。 对应处理流程。
- 处理过程中应用核心业务规则：load_spec_as_params 的 workflow 必须把 spec 内容注入 params。
- 完成后输出并落库/回传：workflow instance、rendered template、execution summary。

## Inputs
- workflow key
- --spec
- --project-dir

## Outputs
- workflow instance
- rendered template
- execution summary

## Business Rules
- load_spec_as_params 的 workflow 必须把 spec 内容注入 params。
- 遇到同 key 运行中 workflow 时要优先恢复或显式重跑。

## Dependencies
- 依赖上游提供：workflow key、--spec

## Non-goals
- 触发 create、run_until_blocked 与 summary 输出。

## Edge Cases
- 当 workflow key 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 通过 CLI 运行 workflow 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：workflow instance、rendered template、execution summary。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 执行 `lee run core.reverse-epic-feat --spec ...` 可创建并运行实例。
- AC-002 CLI summary 会输出最终状态与完成步数。

## Acceptance Checks
### AC-001 执行 `lee run core.reverse-epic-feat --spec ...` 可创建并运行实例。
- Given: 已满足前置条件，且提供 workflow key。
- When: 触发 通过 CLI 运行 workflow 主流程。
- Then: 执行 `lee run core.reverse-epic-feat --spec ...` 可创建并运行实例。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 CLI summary 会输出最终状态与完成步数。
- Given: 系统处于 通过 CLI 运行 workflow 处理中，且相关规则已生效。
- When: 执行与 CLI summary 会输出最终状态与完成步数。 对应的业务步骤。
- Then: 系统应输出/更新：rendered template
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
- `src/lee/cli/commands/run.py`
- `src/lee/cli/main.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/cli/commands/run.py`
- `src/lee/cli/main.py`

## Source Refs
- `src/lee/cli/commands/run.py`
- `src/lee/cli/main.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
