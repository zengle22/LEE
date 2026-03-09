# EPIC-002 工作流执行与门禁控制

## Summary
调度 workflow 步骤、持久化执行状态，并执行自动/人工 gate。

## Scope
覆盖执行、状态机与 gate，不包含业务文档生成策略本身。

## Child Features
- `FEAT-004`
- `FEAT-005`
- `FEAT-006`

## Code Refs
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/state_machine.py`
- `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
- `src/lee/orchestrator/execution/runners/shell_runner.py`
