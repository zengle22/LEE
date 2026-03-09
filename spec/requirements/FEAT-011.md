# FEAT-011 维护模板与实例边界

## Summary
在 workflow spec 维护与评审中强制区分 checked-in 模板和 runtime instance。

## Goal
在 workflow spec 维护与评审中强制区分 checked-in 模板和 runtime instance。

## User Value
用户可以获得 template-boundary compliant spec review result，并完成 维护模板与实例边界 对应业务目标。

## Parent EPIC
- `EPIC-004`

## Capability Linkage
- `CAP-004 SSOT 与治理规则维护`

## Scope
- 在维护 agent 与 review agent 中加入规则。
- 防止 spec 被误描述为运行时实例。

## Preconditions
- 上游已提供完成该能力所需输入：workflow spec change request、review context。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 维护模板与实例边界 后，系统读取并校验所需输入，进入 在 workflow spec 维护与评审中强制区分 checked-in 模板和 runtime instance。 对应处理流程。
- 处理过程中应用核心业务规则：checked-in workflow spec 只能描述模板语义。
- 完成后输出并落库/回传：template-boundary compliant spec review result。

## Processing
- 触发 维护模板与实例边界 后，系统读取并校验所需输入，进入 在 workflow spec 维护与评审中强制区分 checked-in 模板和 runtime instance。 对应处理流程。
- 处理过程中应用核心业务规则：checked-in workflow spec 只能描述模板语义。
- 完成后输出并落库/回传：template-boundary compliant spec review result。

## Inputs
- workflow spec change request
- review context

## Outputs
- template-boundary compliant spec review result

## Business Rules
- checked-in workflow spec 只能描述模板语义。
- 运行时 instance 只能在执行阶段动态生成。

## Dependencies
- 依赖上游提供：workflow spec change request、review context

## Non-goals
- 防止 spec 被误描述为运行时实例。

## Edge Cases
- 当 workflow spec change request 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 维护模板与实例边界 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：template-boundary compliant spec review result。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 workflow spec maintainer 会纠正模板/实例混淆描述。
- AC-002 spec-review 会将该混淆识别为 review finding。

## Acceptance Checks
### AC-001 workflow spec maintainer 会纠正模板/实例混淆描述。
- Given: 已满足前置条件，且提供 workflow spec change request。
- When: 触发 维护模板与实例边界 主流程。
- Then: workflow spec maintainer 会纠正模板/实例混淆描述。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 spec-review 会将该混淆识别为 review finding。
- Given: 系统处于 维护模板与实例边界 处理中，且相关规则已生效。
- When: 执行与 spec-review 会将该混淆识别为 review finding。 对应的业务步骤。
- Then: 系统应输出/更新：template-boundary compliant spec review result
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
- `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
- `spec-global/core/agents/spec-review/v1/agent.yaml`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
- `spec-global/core/agents/spec-review/v1/agent.yaml`

## Source Refs
- `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
- `spec-global/core/agents/spec-review/v1/agent.yaml`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
