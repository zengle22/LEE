# FEAT-010 定义 SSOT 输出契约

## Summary
使用统一 schema 描述 EPIC/FEAT 等 SSOT 输出对象。

## Goal
使用统一 schema 描述 EPIC/FEAT 等 SSOT 输出对象。

## User Value
用户可以获得 contract-compliant ssot-agent-output bundle，并完成 定义 SSOT 输出契约 对应业务目标。

## Parent EPIC
- `EPIC-004`

## Capability Linkage
- `CAP-004 SSOT 与治理规则维护`

## Scope
- 约束 key、identity_kind、ssot_type 与关系字段。
- 让 materialization 与下游工具共享相同 contract。

## Preconditions
- 上游已提供完成该能力所需输入：ssot artifact metadata、content。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 定义 SSOT 输出契约 后，系统读取并校验所需输入，进入 使用统一 schema 描述 EPIC/FEAT 等 SSOT 输出对象。 对应处理流程。
- 处理过程中应用核心业务规则：ssot output 必须声明 ssot_type。
- 完成后输出并落库/回传：contract-compliant ssot-agent-output bundle。

## Processing
- 触发 定义 SSOT 输出契约 后，系统读取并校验所需输入，进入 使用统一 schema 描述 EPIC/FEAT 等 SSOT 输出对象。 对应处理流程。
- 处理过程中应用核心业务规则：ssot output 必须声明 ssot_type。
- 完成后输出并落库/回传：contract-compliant ssot-agent-output bundle。

## Inputs
- ssot artifact metadata
- content

## Outputs
- contract-compliant ssot-agent-output bundle

## Business Rules
- ssot output 必须声明 ssot_type。
- 本 workflow 只允许 epic 与 feat 两种 ssot_type。

## Dependencies
- 依赖上游提供：ssot artifact metadata、content

## Non-goals
- 让 materialization 与下游工具共享相同 contract。

## Edge Cases
- 当 ssot artifact metadata 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 定义 SSOT 输出契约 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：contract-compliant ssot-agent-output bundle。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 生成的 bundle 满足 contract_version=1.0。
- AC-002 outputs 中只出现 epic/feat 两类 SSOT。

## Acceptance Checks
### AC-001 生成的 bundle 满足 contract_version=1.0。
- Given: 已满足前置条件，且提供 ssot artifact metadata。
- When: 触发 定义 SSOT 输出契约 主流程。
- Then: 生成的 bundle 满足 contract_version=1.0。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 outputs 中只出现 epic/feat 两类 SSOT。
- Given: 系统处于 定义 SSOT 输出契约 处理中，且相关规则已生效。
- When: 执行与 outputs 中只出现 epic/feat 两类 SSOT。 对应的业务步骤。
- Then: 系统应输出/更新：contract-compliant ssot-agent-output bundle
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
- `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
- `src/lee/cli/commands/ssot.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
- `src/lee/cli/commands/ssot.py`

## Source Refs
- `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
- `src/lee/cli/commands/ssot.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
