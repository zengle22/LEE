# FEAT-001 注册工作流模板

## Summary
通过 workflow registry 暴露模板定义与参数约束。

## Parent EPIC
- `EPIC-001`

## Capability Linkage
- `CAP-001 工作流模板与实例生成`

## Scope
- 在 registry 中声明 workflow key、path、kind 与参数集合。
- 为 CLI 提供稳定入口。

## Inputs
- workflow key
- template path
- required/optional params

## Outputs
- 可解析的 workflow registry entry

## Business Rules
- registry path 必须指向 checked-in template 文件。
- 模板 spec 只能被描述为模板，不能被视为运行时 instance。

## Acceptance Criteria
- AC-001 给定 workflow key 时，CLI 可以解析到模板路径。
- AC-002 registry 中声明了必填参数 request_id、repo_root、objective。

## Code Refs
- `config/workflow-registry.yaml`
- `src/lee/cli/commands/run.py`

## Evidence Refs
- `config/workflow-registry.yaml`
- `src/lee/cli/commands/run.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
