# FEAT-003 渲染运行时 workflow instance

## Summary
通过 CLI 将模板与参数渲染为运行时 workflow instance 文件并创建实例。

## Goal
通过 CLI 将模板与参数渲染为运行时 workflow instance 文件并创建实例。

## User Value
用户可以获得 .workflow/rendered/*.yaml，并完成 渲染运行时 workflow instance 对应业务目标。

## Parent EPIC
- `EPIC-001`

## Capability Linkage
- `CAP-001 工作流模板与实例生成`

## Scope
- 渲染模板变量、写入 .workflow/rendered。
- 调用 pm_workflow 创建运行时 workflow instance。

## Preconditions
- 上游已提供完成该能力所需输入：template path、params、project_dir。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 渲染运行时 workflow instance 后，系统读取并校验所需输入，进入 通过 CLI 将模板与参数渲染为运行时 workflow instance 文件并创建实例。 对应处理流程。
- 处理过程中应用核心业务规则：rendered workflow 是运行时产物，不应被视为 checked-in spec。
- 完成后输出并落库/回传：.workflow/rendered/*.yaml、workflow instance id。

## Processing
- 触发 渲染运行时 workflow instance 后，系统读取并校验所需输入，进入 通过 CLI 将模板与参数渲染为运行时 workflow instance 文件并创建实例。 对应处理流程。
- 处理过程中应用核心业务规则：rendered workflow 是运行时产物，不应被视为 checked-in spec。
- 完成后输出并落库/回传：.workflow/rendered/*.yaml、workflow instance id。

## Inputs
- template path
- params
- project_dir

## Outputs
- .workflow/rendered/*.yaml
- workflow instance id

## Business Rules
- rendered workflow 是运行时产物，不应被视为 checked-in spec。
- load_spec_as_params 的 workflow 需把 --spec 载入 params。

## Dependencies
- 依赖上游提供：template path、params

## Non-goals
- 调用 pm_workflow 创建运行时 workflow instance。

## Edge Cases
- 当 template path 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 渲染运行时 workflow instance 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：.workflow/rendered/*.yaml、workflow instance id。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 运行 lee run 后会生成 rendered yaml。
- AC-002 runtime instance 的 data.params 与 spec 文件内容一致。

## Acceptance Checks
### AC-001 运行 lee run 后会生成 rendered yaml。
- Given: 已满足前置条件，且提供 template path。
- When: 触发 渲染运行时 workflow instance 主流程。
- Then: 运行 lee run 后会生成 rendered yaml。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 runtime instance 的 data.params 与 spec 文件内容一致。
- Given: 系统处于 渲染运行时 workflow instance 处理中，且相关规则已生效。
- When: 执行与 runtime instance 的 data.params 与 spec 文件内容一致。 对应的业务步骤。
- Then: 系统应输出/更新：workflow instance id
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

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/cli/commands/run.py`

## Source Refs
- `src/lee/cli/commands/run.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
