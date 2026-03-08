# FEAT-002 解析 L3 workflow 模板

## Summary
将 L3 模板中的 stages/steps 解析为可调度步骤与依赖关系。

## Parent EPIC
- `EPIC-001`

## Capability Linkage
- `CAP-001 工作流模板与实例生成`

## Scope
- 解析 stage/step 顺序、outputs、depends_on 与 executor_type。
- 保留模板边界，不生成固定 instance 文件作为规范源。

## Inputs
- rendered template yaml

## Outputs
- workflow steps
- dependency graph
- output specs

## Business Rules
- stage.depends_on 在当前引擎中必须映射到前序 step id。
- kind=skill 的步骤默认走 shell executor。

## Acceptance Criteria
- AC-001 模板可被解析为 Step 列表且不存在循环依赖。
- AC-002 skill/gate 步骤拥有正确 executor_type。

## Code Refs
- `src/lee/orchestrator/execution/template_manager.py`
- `src/lee/orchestrator/ir/converter.py`

## Evidence Refs
- `src/lee/orchestrator/execution/template_manager.py`
- `src/lee/orchestrator/ir/converter.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
