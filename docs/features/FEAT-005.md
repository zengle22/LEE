# FEAT-005 执行自动检查门禁

## Summary
把 step_outputs 扁平化并执行 blocker/major 表达式。

## Parent EPIC
- `EPIC-002`

## Capability Linkage
- `CAP-002 工作流执行与门禁控制`

## Scope
- 构建 gate evaluation context。
- 在 gate fail 时阻塞或失败 workflow。

## Inputs
- gate expression
- step_outputs

## Outputs
- gate pass/fail result

## Business Rules
- freeze 模式要求 blocker 与 major 均为 0。
- gate 上下文允许直接访问 review 输出中的标量字段。

## Acceptance Criteria
- AC-001 review 输出 blocker_count=0 时 draft/publish gate 可通过。
- AC-002 freeze 模式下 major_count>0 会触发 gate fail。

## Code Refs
- `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`

## Evidence Refs
- `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
