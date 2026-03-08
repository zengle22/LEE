# FEAT-006 持久化步骤输出与证据路径

## Summary
完成步骤时把 output dict 与 output paths 写入 workflow data。

## Parent EPIC
- `EPIC-002`

## Capability Linkage
- `CAP-002 工作流执行与门禁控制`

## Scope
- 保存 paths、stdout 元数据与结构化字段。
- 为后续 gate 和 $outputs 引用提供输入。

## Inputs
- step output
- output specs

## Outputs
- workflow.data.step_outputs

## Business Rules
- 同一步骤重复执行时路径列表需要去重合并。
- 结构化 stdout 应合并到 step_outputs 顶层。

## Acceptance Criteria
- AC-001 完成步骤后 step_outputs 中可读取 paths。
- AC-002 gate 表达式可以直接使用 review 产生的 blocker_count。

## Code Refs
- `src/lee/orchestrator/execution/state_machine.py`
- `src/lee/orchestrator/execution/runners/shell_runner.py`

## Evidence Refs
- `src/lee/orchestrator/execution/state_machine.py`
- `src/lee/orchestrator/execution/runners/shell_runner.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
