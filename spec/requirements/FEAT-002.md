# FEAT-002 解析 L3 workflow 模板

## Summary
将 L3 模板中的 stages/steps 解析为可调度步骤与依赖关系。

## Goal
将 L3 模板中的 stages/steps 解析为可调度步骤与依赖关系。

## User Value
用户可以获得 workflow steps，并完成 解析 L3 workflow 模板 对应业务目标。

## Parent EPIC
- `EPIC-001`

## Capability Linkage
- `CAP-001 工作流模板与实例生成`

## Scope
- 解析 stage/step 顺序、outputs、depends_on 与 executor_type。
- 保留模板边界，不生成固定 instance 文件作为规范源。

## Preconditions
- 上游已提供完成该能力所需输入：rendered template yaml。
- 相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。

## Main Flow
- 触发 解析 L3 workflow 模板 后，系统读取并校验所需输入，进入 将 L3 模板中的 stages/steps 解析为可调度步骤与依赖关系。 对应处理流程。
- 处理过程中应用核心业务规则：stage.depends_on 在当前引擎中必须映射到前序 step id。
- 完成后输出并落库/回传：workflow steps、dependency graph、output specs。

## Processing
- 触发 解析 L3 workflow 模板 后，系统读取并校验所需输入，进入 将 L3 模板中的 stages/steps 解析为可调度步骤与依赖关系。 对应处理流程。
- 处理过程中应用核心业务规则：stage.depends_on 在当前引擎中必须映射到前序 step id。
- 完成后输出并落库/回传：workflow steps、dependency graph、output specs。

## Inputs
- rendered template yaml

## Outputs
- workflow steps
- dependency graph
- output specs

## Business Rules
- stage.depends_on 在当前引擎中必须映射到前序 step id。
- kind=skill 的步骤默认走 shell executor。

## Dependencies
- 依赖上游提供：rendered template yaml

## Non-goals
- 保留模板边界，不生成固定 instance 文件作为规范源。

## Edge Cases
- 当 rendered template yaml 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。
- 当 解析 L3 workflow 模板 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。

## State Updates
- 成功执行后更新相关业务状态：workflow steps、dependency graph、output specs。
- 若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。

## Acceptance Criteria
- AC-001 模板可被解析为 Step 列表且不存在循环依赖。
- AC-002 skill/gate 步骤拥有正确 executor_type。

## Acceptance Checks
### AC-001 模板可被解析为 Step 列表且不存在循环依赖。
- Given: 已满足前置条件，且提供 rendered template yaml。
- When: 触发 解析 L3 workflow 模板 主流程。
- Then: 模板可被解析为 Step 列表且不存在循环依赖。
- Trace Hints: TASK, TESTSET, UI, TECH
### AC-002 skill/gate 步骤拥有正确 executor_type。
- Given: 系统处于 解析 L3 workflow 模板 处理中，且相关规则已生效。
- When: 执行与 skill/gate 步骤拥有正确 executor_type。 对应的业务步骤。
- Then: 系统应输出/更新：dependency graph
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
- `src/lee/orchestrator/execution/template_manager.py`
- `src/lee/orchestrator/ir/converter.py`

## Evidence Layers
### Impl Refs
### API Refs
### Test Refs
### Doc Refs

## Evidence Refs
- `src/lee/orchestrator/execution/template_manager.py`
- `src/lee/orchestrator/ir/converter.py`

## Source Refs
- `src/lee/orchestrator/execution/template_manager.py`
- `src/lee/orchestrator/ir/converter.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
