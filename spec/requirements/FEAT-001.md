# FEAT-001 注册工作流模板

## Summary
通过 workflow registry 暴露模板定义与参数约束。

## Goal
通过 workflow registry 暴露模板定义与参数约束。

## User Value
用户可以获得 可解析的 workflow registry entry，并完成 注册工作流模板 对应业务目标。

## Parent EPIC
- `EPIC-001`

## Capability Linkage
- `CAP-001 工作流模板与实例生成`

## Scope
- 在 registry 中声明 workflow key、path、kind 与参数集合。
- 为 CLI 提供稳定入口。

## Preconditions
- 上游已提供完成该能力所需输入：workflow key、template path、required/optional params。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 注册工作流模板 后，系统读取并校验所需输入，进入 通过 workflow registry 暴露模板定义与参数约束。 对应处理流程。
- 处理过程中应用核心业务规则：registry path 必须指向 checked-in template 文件。
- 完成后输出并落库/回传：可解析的 workflow registry entry。

## Processing
- 触发 注册工作流模板 后，系统读取并校验所需输入，进入 通过 workflow registry 暴露模板定义与参数约束。 对应处理流程。
- 处理过程中应用核心业务规则：registry path 必须指向 checked-in template 文件。
- 完成后输出并落库/回传：可解析的 workflow registry entry。

## Inputs
- workflow key
- template path
- required/optional params

## Outputs
- 可解析的 workflow registry entry

## Business Rules
- registry path 必须指向 checked-in template 文件。
- 模板 spec 只能被描述为模板，不能被视为运行时 instance。

## Dependencies
- 依赖上游提供：workflow key、template path

## Non-goals
- 为 CLI 提供稳定入口。

## Edge Cases
- 当 workflow key 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 注册工作流模板 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：可解析的 workflow registry entry。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 给定 workflow key 时，CLI 可以解析到模板路径。
- AC-002 registry 中声明了必填参数 request_id、repo_root、objective。

## Acceptance Checks
### AC-001 给定 workflow key 时，CLI 可以解析到模板路径。
- Given: 已满足前置条件，且提供 workflow key。
- When: 触发 注册工作流模板 主流程。
- Then: 给定 workflow key 时，CLI 可以解析到模板路径。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 registry 中声明了必填参数 request_id、repo_root、objective。
- Given: 系统处于 注册工作流模板 处理中，且相关规则已生效。
- When: 执行与 registry 中声明了必填参数 request_id、repo_root、objective。 对应的业务步骤。
- Then: 系统应输出/更新：可解析的 workflow registry entry
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
- `config/workflow-registry.yaml`
- `src/lee/cli/commands/run.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `config/workflow-registry.yaml`
- `src/lee/cli/commands/run.py`

## Source Refs
- `config/workflow-registry.yaml`
- `src/lee/cli/commands/run.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
