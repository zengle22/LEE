# FEAT-003 渲染运行时 workflow instance

## Summary
通过 CLI 将模板与参数渲染为运行时 workflow instance 文件并创建实例。

## Parent EPIC
- `EPIC-001`

## Capability Linkage
- `CAP-001 工作流模板与实例生成`

## Scope
- 渲染模板变量、写入 .workflow/rendered。
- 调用 pm_workflow 创建运行时 workflow instance。

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

## Acceptance Criteria
- AC-001 运行 lee run 后会生成 rendered yaml。
- AC-002 runtime instance 的 data.params 与 spec 文件内容一致。

## Code Refs
- `src/lee/cli/commands/run.py`

## Evidence Refs
- `src/lee/cli/commands/run.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
