# FEAT-007 通过 CLI 运行 workflow

## Summary
支持 `lee run` 加载 registry、渲染模板并执行 workflow。

## Parent EPIC
- `EPIC-003`

## Capability Linkage
- `CAP-003 CLI 工作流操作`

## Scope
- 解析 workflow key 与 spec 文件。
- 触发 create、run_until_blocked 与 summary 输出。

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

## Acceptance Criteria
- AC-001 执行 `lee run core.reverse-epic-feat --spec ...` 可创建并运行实例。
- AC-002 CLI summary 会输出最终状态与完成步数。

## Code Refs
- `src/lee/cli/commands/run.py`
- `src/lee/cli/main.py`

## Evidence Refs
- `src/lee/cli/commands/run.py`
- `src/lee/cli/main.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
